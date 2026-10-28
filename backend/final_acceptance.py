"""Repeatable isolated MySQL acceptance, synthetic seed and verified backup/restore."""

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from typing import Any

import mysql.connector
from backend.config import Settings
from backend.db import Database
from backend.demo_data import seed
from backend.migrations import migrate

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SYNTHETIC_PASSWORD = "Synthetic-Test-Only-2026!"


def database_fingerprint(connection: Any, name: str) -> dict[str, dict[str, int | str]]:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME",
        (name,),
    )
    tables = [row[0] for row in cursor.fetchall()]
    result = {}
    for table in tables:
        assert table.replace("_", "").isalnum()
        cursor.execute(f"SELECT * FROM `{name}`.`{table}`")
        rows = sorted(
            json.dumps(row, default=str, ensure_ascii=False)
            for row in cursor.fetchall()
        )
        result[table] = {
            "count": len(rows),
            "sha256": hashlib.sha256("\n".join(rows).encode()).hexdigest(),
        }
    cursor.close()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isolated-server", action="store_true")
    parser.add_argument("--port", type=int, default=33316)
    parser.add_argument(
        "--mysql-bin", default="C:/Program Files/MySQL/MySQL Server 8.0/bin"
    )
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use a non-privileged local test port")
    stamp = (
        datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        + "_"
        + secrets.token_hex(3)
    )
    runtime = ROOT / ".mysql-test" / ("acceptance_" + stamp)
    runtime.mkdir(parents=True)
    reportdir = ROOT / "docs/reports/final-acceptance-20261029"
    reportdir.mkdir(parents=True, exist_ok=True)
    process = None
    admin = None
    db = None
    mysqlbin = Path(args.mysql_bin)
    options = {
        "host": "127.0.0.1",
        "port": args.port,
        "user": "root",
        "password": "" if args.isolated_server else os.environ.get("DB_PASSWORD", ""),
        "connection_timeout": 5,
        "charset": "utf8mb4",
        "collation": "utf8mb4_0900_ai_ci",
    }
    if args.isolated_server:
        if args.port == 3306:
            parser.error("Isolated test server must not use the application port 3306")
        subprocess.run(
            [
                str(mysqlbin / "mysqld.exe"),
                "--no-defaults",
                "--initialize-insecure",
                f"--basedir={mysqlbin.parent}",
                f'--datadir={runtime/"data"}',
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        process = subprocess.Popen(
            [
                str(mysqlbin / "mysqld.exe"),
                "--no-defaults",
                f"--basedir={mysqlbin.parent}",
                f'--datadir={runtime/"data"}',
                f"--port={args.port}",
                "--bind-address=127.0.0.1",
                "--mysqlx=OFF",
                f'--log-error={runtime/"mysql.log"}',
            ],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("Isolated MySQL failed; inspect its runtime log")
            try:
                admin = mysql.connector.connect(**options)
                break
            except mysql.connector.Error:
                time.sleep(0.5)
        if admin is None:
            raise RuntimeError("Isolated MySQL did not become ready")
    else:
        admin = mysql.connector.connect(**options)
    report = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "python": platform.python_version(),
            "os": platform.platform(),
            "cpu": platform.processor(),
            "logical_cpus": os.cpu_count(),
        },
        "provider": "deterministic SIMULATION; transport tests exercise real provider adapters without Internet",
        "limitations": [
            "Live Gemini quality/latency/quota not verified without a supplied provider key",
            "Production HTTPS, uptime and compliance certification not asserted",
        ],
        "status": "RUNNING",
    }
    try:
        cursor = admin.cursor()
        cursor.execute("SELECT VERSION(),@@port,@@datadir")
        version, port, datadir = cursor.fetchone()
        cursor.close()
        if not version.startswith("8.0.46") or port != args.port:
            raise RuntimeError("Unexpected MySQL version or port")
        report["mysql"] = {"version": version, "port": port, "datadir": datadir}
        demo = "vietincare_demo_" + stamp
        restore = "vietincare_restore_" + stamp
        base = Settings.from_env(
            {"APP_ORIGIN": "http://localhost:3000", "AI_PROVIDER": "gemini"}
        )
        settings = replace(base, database={**options, "database": demo})
        report["migration"] = migrate(settings, initialize=True)
        db = Database(settings.database)
        report["seed"] = seed(db, PUBLIC_SYNTHETIC_PASSWORD)
        report["demo_database"] = demo
        print("Synthetic demo data loaded; running all acceptance tests.", flush=True)
        env = os.environ.copy()
        env.update(
            {
                "RUN_MYSQL_TESTS": "1",
                "DB_HOST": "127.0.0.1",
                "DB_PORT": str(args.port),
                "DB_USER": "root",
                "DB_PASSWORD": str(options["password"]),
                "DB_NAME": demo,
                "APP_ORIGIN": "http://localhost:3000",
                "COOKIE_SECURE": "false",
                "AI_PROVIDER": "gemini",
            }
        )
        for key in ["OPENAI_API_KEY", "GEMINI_API_KEY", "TWILIO_AUTH_TOKEN"]:
            env.pop(key, None)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-ra",
                f'--junitxml={reportdir/"pytest.xml"}',
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        (reportdir / "pytest.log").write_text(result.stdout, encoding="utf-8")
        print(result.stdout, flush=True)
        tree = ET.parse(reportdir / "pytest.xml")
        suites = tree.getroot().findall("testsuite")
        report["pytest"] = {
            key: sum(int(s.get(key, 0)) for s in suites)
            for key in ["tests", "failures", "errors", "skipped"]
        }
        report["pytest"]["exit_code"] = result.returncode
        original = database_fingerprint(admin, demo)
        sql_backup = runtime / "synthetic-demo-backup.sql"
        dump = [
            str(mysqlbin / "mysqldump.exe"),
            "--no-defaults",
            "--host=127.0.0.1",
            f"--port={args.port}",
            "--user=root",
            "--single-transaction",
            "--skip-add-drop-table",
            "--skip-add-locks",
            "--no-tablespaces",
            "--set-gtid-purged=OFF",
            "--column-statistics=0",
            demo,
        ]
        childenv = os.environ.copy()
        childenv["MYSQL_PWD"] = str(options["password"])
        with sql_backup.open("wb") as stream:
            subprocess.run(
                dump, env=childenv, stdout=stream, stderr=subprocess.PIPE, check=True
            )
        cursor = admin.cursor()
        cursor.execute(
            f"CREATE DATABASE `{restore}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
        )
        cursor.close()
        with sql_backup.open("rb") as stream:
            subprocess.run(
                [
                    str(mysqlbin / "mysql.exe"),
                    "--no-defaults",
                    "--host=127.0.0.1",
                    f"--port={args.port}",
                    "--user=root",
                    "--default-character-set=utf8mb4",
                    restore,
                ],
                env=childenv,
                stdin=stream,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True,
            )
        restored = database_fingerprint(admin, restore)
        if original != restored:
            raise AssertionError("Backup/restore row contents differ")
        check = migrate(
            replace(settings, database={**settings.database, "database": restore}),
            check=True,
        )
        report["backup_restore"] = {
            "status": "PASS",
            "tables": len(original),
            "rows": sum(r["count"] for r in original.values()),
            "every_table_count_and_content_sha256_match": True,
            "migration_check": check,
        }
        report["data_counts"] = original
        performance = reportdir / "performance-simulation.json"
        if performance.is_file():
            report["performance_simulation"] = json.loads(performance.read_text())
        report["status"] = (
            "PASS_AUTOMATED_DEMO"
            if result.returncode == 0 and report["pytest"]["skipped"] == 0
            else "INCOMPLETE"
        )
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    except Exception as error:
        report["status"] = "FAILED"
        report["error_type"] = type(error).__name__
        raise
    finally:
        if db is not None:
            db.pool._remove_connections()
        (reportdir / "result.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if process is not None and admin is not None:
            cursor = admin.cursor()
            cursor.execute("SELECT @@datadir")
            actual = Path(cursor.fetchone()[0]).resolve()
            cursor.close()
            if actual != (runtime / "data").resolve():
                raise RuntimeError("Refusing to stop an unrelated MySQL server")
            cursor = admin.cursor()
            try:
                cursor.execute("SHUTDOWN")
            except mysql.connector.Error:
                pass
            cursor.close()
            process.wait(timeout=30)
        if admin is not None:
            admin.close()
    print(
        json.dumps(
            {
                "status": report["status"],
                "tests": report["pytest"],
                "report": str(reportdir / "result.json"),
            },
            ensure_ascii=True,
        )
    )
    if report["status"] != "PASS_AUTOMATED_DEMO":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Local-only browser acceptance server. Requires an explicit synthetic demo database."""

import argparse
from dataclasses import replace
import os
import re
import secrets

import mysql.connector
import uvicorn
from backend.app import create_app
from backend.config import Settings
from backend.db import Database
from backend.demo_ai import SimulationAI


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--mysql-port", type=int, default=33316)
    parser.add_argument("--port", type=int, default=3001)
    args = parser.parse_args()
    if not re.fullmatch(r"vietincare_demo_[0-9_]+[0-9a-f]{6}", args.database):
        parser.error(
            "Only a synthetic database produced by final_acceptance is allowed"
        )
    options = {
        "host": "127.0.0.1",
        "port": args.mysql_port,
        "user": "root",
        "password": os.getenv("DB_PASSWORD", ""),
        "database": args.database,
    }
    user = "vc_browser_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    admin = mysql.connector.connect(**options)
    cursor = admin.cursor()
    for host in ["localhost", "127.0.0.1"]:
        cursor.execute(f"CREATE USER '{user}'@'{host}' IDENTIFIED BY %s", (password,))
        cursor.execute(
            f"GRANT SELECT,INSERT,UPDATE,DELETE ON `{args.database}`.* TO '{user}'@'{host}'"
        )
    cursor.close()
    settings = Settings.from_env(
        {"APP_ORIGIN": f"http://localhost:{args.port}", "AI_PROVIDER": "gemini"}
    )
    settings = replace(
        settings,
        database={**settings.database, **options, "user": user, "password": password},
    )
    db = Database(settings.database)
    try:
        uvicorn.run(
            create_app(
                database=db, settings=settings, ai=SimulationAI(), serve_static=True
            ),
            host="127.0.0.1",
            port=args.port,
            log_level="warning",
        )
    finally:
        db.pool._remove_connections()
        cursor = admin.cursor()
        for host in ["localhost", "127.0.0.1"]:
            cursor.execute(f"DROP USER '{user}'@'{host}'")
        cursor.close()
        admin.close()


if __name__ == "__main__":
    main()

import os

import mysql.connector


APP_USER = "vietincare_app"
APP_HOSTS = ("localhost", "127.0.0.1")
DATABASE = "qlkhviettin"


class SetupFailure(RuntimeError):
    def __init__(self, code: str, account_created: bool):
        super().__init__(code)
        self.account_created = account_created


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def setup(root_password: str, app_password: str) -> None:
    if len(app_password) < 12:
        raise ValueError("SETUP_INPUT_REQUIRED")
    admin = mysql.connector.connect(
        host="127.0.0.1", port=3306, user="root", password=root_password,
        connection_timeout=5, charset="utf8mb4", collation="utf8mb4_0900_ai_ci",
    )
    app_connection = None
    created = False
    try:
        cursor = admin.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT VERSION() version")
        version = cursor.fetchone()["version"]
        if not str(version).startswith("8.0.46"):
            raise ValueError("MYSQL_VERSION_REQUIRED")
        cursor.execute(f"SELECT TokenHash FROM `{DATABASE}`.AuthSession LIMIT 0")
        cursor.execute("SET SESSION sql_mode = 'NO_BACKSLASH_ESCAPES'")
        for app_host in APP_HOSTS:
            cursor.execute(f"CREATE USER IF NOT EXISTS '{APP_USER}'@'{app_host}' IDENTIFIED BY {_literal(app_password)}")
            cursor.execute(f"ALTER USER '{APP_USER}'@'{app_host}' IDENTIFIED BY {_literal(app_password)}")
            cursor.execute(f"GRANT SELECT,INSERT,UPDATE,DELETE ON `{DATABASE}`.* TO '{APP_USER}'@'{app_host}'")
        created = True
        cursor.close()
        admin.commit()
        app_connection = mysql.connector.connect(
            host="127.0.0.1", port=3306, user=APP_USER, password=app_password, database=DATABASE,
            connection_timeout=5, charset="utf8mb4", collation="utf8mb4_0900_ai_ci", time_zone="+00:00",
        )
        identity_cursor = app_connection.cursor(dictionary=True, buffered=True)
        identity_cursor.execute("SELECT CURRENT_USER() identity")
        identity = identity_cursor.fetchone()["identity"]
        if identity not in {f"{APP_USER}@{app_host}" for app_host in APP_HOSTS}:
            raise ValueError("UNEXPECTED_APP_IDENTITY")
        identity_cursor.execute("SELECT TokenHash FROM AuthSession LIMIT 0")
        identity_cursor.fetchall()
        identity_cursor.close()
    except mysql.connector.Error as error:
        safe_code = error.errno if error.errno in {1044, 1045, 1049, 1054, 1142, 1146, 1396} else "SETUP_FAILED"
        raise SetupFailure(str(safe_code), created) from None
    finally:
        if app_connection:
            app_connection.close()
        admin.close()
    print("APP_USER_READY: vietincare_app@localhost/127.0.0.1; project data privileges only.")
    if created:
        return


def main() -> None:
    root_password = os.environ.get("VIETINCARE_SETUP_ROOT_PASSWORD", "")
    app_password = os.environ.get("VIETINCARE_SETUP_APP_PASSWORD", "")
    if not root_password or not app_password:
        print("SETUP_INPUT_REQUIRED")
        raise SystemExit(1)
    try:
        setup(root_password, app_password)
    except SetupFailure as error:
        print(error)
        if error.account_created:
            print("APP_USER_UPDATED: credentials and grants were applied; rerun setup to repeat the verification safely.")
        raise SystemExit(1) from None
    except Exception as error:
        print(str(error) if str(error) in {"MYSQL_VERSION_REQUIRED", "UNEXPECTED_APP_IDENTITY", "SETUP_INPUT_REQUIRED"} or str(error).isdigit() else "SETUP_FAILED")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

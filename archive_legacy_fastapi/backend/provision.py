import os
import re
import secrets

from backend.config import Settings
from backend.db import Database
from backend.security import hash_password


def create_staff(role_name: str, name: str, email: str, password: str, settings: Settings) -> None:
    email = email.strip().lower()
    name = name.strip()
    if role_name not in {"Agent", "Admin"}:
        raise ValueError("INVALID_ROLE")
    if not name or len(name) > 100 or len(email) > 100 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError(f"INVALID_{role_name.upper()}_INPUT")
    if not 12 <= len(password) <= 128:
        raise ValueError(f"INVALID_{role_name.upper()}_INPUT")
    database = Database(settings.database)
    password_hash = hash_password(password)
    with database.transaction() as transaction:
        role = transaction.fetch_one("SELECT MaRole FROM Role WHERE TenRole=?", (role_name,))
        if not role:
            raise ValueError("MIGRATION_REQUIRED")
        user_id = transaction.execute(
            "INSERT INTO UserAccount(MaRole,HoTen,Username,Email,PasswordHash) VALUES(?,?,?,?,?)",
            (role["MaRole"], name, f"{role_name.lower()}_{secrets.token_hex(12)}", email, password_hash),
        )
        transaction.execute(
            "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong) VALUES(?,?, 'UserAccount',?)",
            (user_id, f"{role_name.upper()}_CREATE_LOCAL", user_id),
        )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=("Agent", "Admin"), required=True)
    args = parser.parse_args()
    prefix = "VC_AGENT" if args.role == "Agent" else "VC_ADMIN"
    try:
        create_staff(
            args.role,
            os.environ.get(f"{prefix}_NAME", ""),
            os.environ.get(f"{prefix}_EMAIL", ""),
            os.environ.get(f"{prefix}_PASSWORD", ""),
            Settings.from_env(),
        )
        print("AGENT_CREATED" if args.role == "Agent" else "ADMIN_CREATED")
    except Exception as error:
        safe_code = str(error) if str(error).startswith(("INVALID_", "MIGRATION_REQUIRED")) else getattr(error, "errno", None) or "PROVISION_FAILED"
        print(safe_code)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
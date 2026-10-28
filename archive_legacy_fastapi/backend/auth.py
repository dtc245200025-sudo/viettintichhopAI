import hashlib
import hmac
import re
import secrets
from typing import Any

import mysql.connector.errors
from fastapi import FastAPI, Request, Response

from backend.config import Settings
from backend.db import Database, Transaction
from backend.errors import ApiError
from backend.security import digest, hash_password, new_session_token, verify_password
from backend.sms import TwilioSmsSender


ROLES = {"Customer", "Agent", "Supervisor", "Admin"}
EMAIL_RE = re.compile(r"^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+$", re.IGNORECASE)
PHONE_RE = re.compile(r"^\+?[0-9 ()-]{8,20}$")
TOKEN_RE = re.compile(r"^[a-f0-9]{64}$")


def _audit(transaction: Transaction, user_id: int, action: str, ip: str | None) -> None:
    transaction.execute(
        "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,'UserAccount',?,?)",
        (user_id, action, user_id, ip),
    )


def _throttle(transaction: Transaction, key: str, limit: int) -> bool:
    key_hash = digest(key)
    transaction.execute(
        "INSERT IGNORE INTO AuthThrottle(ThrottleKey,Attempts,WindowEnd) "
        "VALUES(?,0,DATE_ADD(UTC_TIMESTAMP(3),INTERVAL 15 MINUTE))",
        (key_hash,),
    )
    row = transaction.fetch_one(
        "SELECT Attempts,WindowEnd<=UTC_TIMESTAMP(3) expired FROM AuthThrottle WHERE ThrottleKey=? FOR UPDATE",
        (key_hash,),
    )
    if not row:
        return False
    if not row["expired"] and row["Attempts"] >= limit:
        return False
    transaction.execute(
        "UPDATE AuthThrottle SET Attempts=IF(WindowEnd<=UTC_TIMESTAMP(3),1,Attempts+1),"
        "WindowEnd=IF(WindowEnd<=UTC_TIMESTAMP(3),DATE_ADD(UTC_TIMESTAMP(3),INTERVAL 15 MINUTE),WindowEnd) "
        "WHERE ThrottleKey=?",
        (key_hash,),
    )
    return True


def _cookie_token(request: Request) -> str | None:
    matches = re.findall(r"(?:^|;\s*)vietincare_session=([^;]*)", request.headers.get("cookie", ""))
    if len(matches) != 1 or not TOKEN_RE.fullmatch(matches[0]):
        return None
    return matches[0]


def current_user(request: Request, database: Database) -> dict[str, Any]:
    token = _cookie_token(request)
    if token is None:
        raise ApiError(401, "UNAUTHENTICATED")
    user = database.fetch_one(
        "SELECT u.MaUser,u.HoTen,u.Email,r.TenRole,c.MaKH "
        "FROM AuthSession s JOIN UserAccount u ON u.MaUser=s.MaUser "
        "JOIN Role r ON r.MaRole=u.MaRole LEFT JOIN Customer c ON c.MaUser=u.MaUser "
        "WHERE s.TokenHash=? AND s.ExpiresAt>UTC_TIMESTAMP(3) AND u.TrangThai=1 "
        "AND (r.TenRole<>'Customer' OR (c.MaKH IS NOT NULL AND c.TrangThai=1))",
        (digest(token),),
    )
    if not user or user["TenRole"] not in ROLES:
        raise ApiError(401, "UNAUTHENTICATED")
    user["_token"] = token
    return user


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["MaUser"],
        "name": user["HoTen"],
        "email": user["Email"],
        "role": user["TenRole"],
        "customerId": user.get("MaKH"),
    }


def _require_role(user: dict[str, Any], *roles: str) -> None:
    if user["TenRole"] not in roles:
        raise ApiError(403, "FORBIDDEN")


def _e164_phone(value: str) -> str | None:
    value = value.strip()
    if not PHONE_RE.fullmatch(value):
        return None
    digits = re.sub(r"\D", "", value)
    if value.startswith("+") and digits.startswith("0"):
        return None
    if not value.startswith("+") and digits.startswith("0"):
        digits = f"84{digits[1:]}"
    if not 8 <= len(digits) <= 15 or digits.startswith("0"):
        return None
    return f"+{digits}"


def _otp_hash(salt: str, code: str) -> str:
    return hashlib.scrypt(code.encode("ascii"), salt=bytes.fromhex(salt), n=2**14, r=8, p=1, dklen=32).hex()


def install_auth_routes(
    app: FastAPI,
    database: Database,
    settings: Settings,
    sms_sender: TwilioSmsSender | None = None,
) -> None:
    sms_sender = sms_sender or TwilioSmsSender(settings)

    @app.post("/api/auth/register", status_code=201)
    def register(payload: dict[str, Any], request: Request) -> dict[str, str]:
        email = payload.get("email", "")
        name = payload.get("fullName", "")
        phone = payload.get("phone", "")
        password = payload.get("password")
        if not all(isinstance(value, str) for value in (email, name, phone, password)):
            raise ApiError(400, "INVALID_INPUT")
        email = email.strip().lower()
        name = name.strip()
        phone = phone.strip()
        if (
            not EMAIL_RE.fullmatch(email)
            or len(email) > 100
            or not name
            or len(name) > 100
            or not PHONE_RE.fullmatch(phone)
            or not 8 <= len(password) <= 128
            or payload.get("acceptTerms") is not True
        ):
            raise ApiError(400, "INVALID_INPUT")

        with database.transaction() as transaction:
            if not _throttle(transaction, f"register:{request.client.host if request.client else ''}", 20):
                raise ApiError(429, "RATE_LIMITED")
        password_hash = hash_password(password)
        try:
            with database.transaction() as transaction:
                role = transaction.fetch_one("SELECT MaRole FROM Role WHERE TenRole='Customer'")
                if not role:
                    raise RuntimeError("Database migrations are required")
                user_id = transaction.execute(
                    "INSERT INTO UserAccount(MaRole,HoTen,Username,PasswordHash,Email,SoDienThoai) VALUES(?,?,?,?,?,?)",
                    (role["MaRole"], name, f"customer_{secrets.token_hex(16)}", password_hash, email, phone),
                )
                transaction.execute(
                    "INSERT INTO Customer(MaUser,HoTen,Email,SoDienThoai,LoaiKhachHang) VALUES(?,?,?,?,?)",
                    (user_id, name, email, phone, "Cá nhân"),
                )
                _audit(transaction, user_id, "REGISTER", request.client.host if request.client else None)
        except mysql.connector.errors.IntegrityError as error:
            if error.errno == 1062:
                raise ApiError(409, "EMAIL_EXISTS") from error
            raise
        return {"message": "REGISTERED"}

    @app.post("/api/auth/login")
    def login(payload: dict[str, Any], request: Request, response: Response) -> dict[str, Any]:
        email = payload.get("email", "")
        password = payload.get("password")
        if not isinstance(email, str) or not isinstance(password, str):
            raise ApiError(400, "INVALID_INPUT")
        email = email.strip().lower()
        if not EMAIL_RE.fullmatch(email) or len(email) > 100 or not 8 <= len(password) <= 128:
            raise ApiError(400, "INVALID_INPUT")
        ip = request.client.host if request.client else ""
        with database.transaction() as transaction:
            allowed = _throttle(transaction, f"login-ip:{ip}", 40)
            allowed = _throttle(transaction, f"login-email:{email}", 5) and allowed
        user = database.fetch_one(
            "SELECT u.*,r.TenRole,c.MaKH,c.TrangThai CustomerActive FROM UserAccount u "
            "JOIN Role r ON r.MaRole=u.MaRole LEFT JOIN Customer c ON c.MaUser=u.MaUser "
            "WHERE u.EmailNormalized=?",
            (email,),
        )
        valid_password = verify_password(password, user.get("PasswordHash") if user else None)
        if (
            not allowed
            or not valid_password
            or not user
            or not user["TrangThai"]
            or user["TenRole"] not in ROLES
            or (user["TenRole"] == "Customer" and (not user["MaKH"] or not user["CustomerActive"]))
        ):
            raise ApiError(429 if not allowed else 401, "RATE_LIMITED" if not allowed else "INVALID_CREDENTIALS")

        token = new_session_token()
        with database.transaction() as transaction:
            previous = _cookie_token(request)
            if previous:
                transaction.execute("DELETE FROM AuthSession WHERE TokenHash=?", (digest(previous),))
            transaction.execute(
                "INSERT INTO AuthSession(TokenHash,MaUser,ExpiresAt) VALUES(?,?,TIMESTAMPADD(HOUR,?,UTC_TIMESTAMP(3)))",
                (digest(token), user["MaUser"], settings.session_hours),
            )
            transaction.execute("DELETE FROM AuthThrottle WHERE ThrottleKey=?", (digest(f"login-email:{email}"),))
            _audit(transaction, user["MaUser"], "LOGIN", ip)
        response.set_cookie(
            "vietincare_session",
            token,
            max_age=settings.session_hours * 3600,
            httponly=True,
            secure=settings.secure_cookie,
            samesite="strict",
            path="/",
        )
        return {"user": _public_user(user)}

    @app.post("/api/auth/otp/request")
    def request_otp(payload: dict[str, Any], request: Request) -> dict[str, str]:
        raw_phone = payload.get("phone", "")
        phone = _e164_phone(raw_phone) if isinstance(raw_phone, str) else None
        if phone is None:
            raise ApiError(400, "INVALID_INPUT")
        if not sms_sender.configured:
            raise ApiError(503, "OTP_UNAVAILABLE")

        ip = request.client.host if request.client else ""
        code = f"{secrets.randbelow(1_000_000):06d}"
        salt = secrets.token_hex(16)
        challenge_id = None
        with database.transaction() as transaction:
            transaction.execute("DELETE FROM AuthOtpChallenge WHERE ExpiresAt<=UTC_TIMESTAMP(3)")
            allowed = _throttle(transaction, f"otp-send-ip:{ip}", 10)
            allowed = _throttle(transaction, f"otp-send-phone:{phone}", 3) and allowed
            if allowed:
                phone_digits = phone[1:]
                user = transaction.fetch_one(
                    "SELECT MIN(u.MaUser) MaUser FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole "
                    "LEFT JOIN Customer c ON c.MaUser=u.MaUser "
                    "WHERE CASE WHEN LEFT(REGEXP_REPLACE(u.SoDienThoai,'[^0-9]',''),1)='0' "
                    "THEN CONCAT('84',SUBSTRING(REGEXP_REPLACE(u.SoDienThoai,'[^0-9]',''),2)) "
                    "ELSE REGEXP_REPLACE(u.SoDienThoai,'[^0-9]','') END=? "
                    "AND u.TrangThai=1 AND (r.TenRole<>'Customer' OR (c.MaKH IS NOT NULL AND c.TrangThai=1)) "
                    "HAVING COUNT(DISTINCT u.MaUser)=1",
                    (phone_digits,),
                )
                if user:
                    transaction.execute("DELETE FROM AuthOtpChallenge WHERE SoDienThoaiE164=?", (phone,))
                    challenge_id = transaction.execute(
                        "INSERT INTO AuthOtpChallenge(MaUser,SoDienThoaiE164,CodeHash,CodeSalt,ExpiresAt) "
                        "VALUES(?,?,?,?,TIMESTAMPADD(MINUTE,5,UTC_TIMESTAMP(3)))",
                        (user["MaUser"], phone, _otp_hash(salt, code), salt),
                    )
        if not allowed:
            raise ApiError(429, "RATE_LIMITED")
        if challenge_id is not None:
            try:
                sms_sender.send_otp(phone, code)
            except RuntimeError as error:
                with database.transaction() as transaction:
                    transaction.execute("DELETE FROM AuthOtpChallenge WHERE MaChallenge=?", (challenge_id,))
                raise ApiError(503, "OTP_UNAVAILABLE") from error
        return {"message": "OTP_SENT"}

    @app.post("/api/auth/otp/verify")
    def verify_otp(payload: dict[str, Any], request: Request, response: Response) -> dict[str, Any]:
        raw_phone = payload.get("phone", "")
        code = payload.get("code", "")
        phone = _e164_phone(raw_phone) if isinstance(raw_phone, str) else None
        if phone is None or not isinstance(code, str) or not re.fullmatch(r"\d{6}", code):
            raise ApiError(400, "INVALID_INPUT")
        ip = request.client.host if request.client else ""
        user = None
        with database.transaction() as transaction:
            allowed = _throttle(transaction, f"otp-verify-ip:{ip}", 30)
            allowed = _throttle(transaction, f"otp-verify-phone:{phone}", 5) and allowed
            challenge = transaction.fetch_one(
                "SELECT MaChallenge,MaUser,CodeHash,CodeSalt,Attempts,ExpiresAt>UTC_TIMESTAMP(3) Valid "
                "FROM AuthOtpChallenge WHERE SoDienThoaiE164=? ORDER BY CreatedAt DESC LIMIT 1 FOR UPDATE",
                (phone,),
            ) if allowed else None
            if challenge and challenge["Valid"] and challenge["Attempts"] < 5:
                transaction.execute("UPDATE AuthOtpChallenge SET Attempts=Attempts+1 WHERE MaChallenge=?", (challenge["MaChallenge"],))
                if hmac.compare_digest(challenge["CodeHash"], _otp_hash(challenge["CodeSalt"], code)):
                    user = transaction.fetch_one(
                        "SELECT u.*,r.TenRole,c.MaKH,c.TrangThai CustomerActive FROM UserAccount u "
                        "JOIN Role r ON r.MaRole=u.MaRole LEFT JOIN Customer c ON c.MaUser=u.MaUser "
                        "WHERE u.MaUser=? AND u.TrangThai=1 AND (r.TenRole<>'Customer' OR (c.MaKH IS NOT NULL AND c.TrangThai=1)) FOR UPDATE",
                        (challenge["MaUser"],),
                    )
                    if user and user["TenRole"] in ROLES:
                        transaction.execute("DELETE FROM AuthOtpChallenge WHERE MaChallenge=?", (challenge["MaChallenge"],))
                        token = new_session_token()
                        previous = _cookie_token(request)
                        if previous:
                            transaction.execute("DELETE FROM AuthSession WHERE TokenHash=?", (digest(previous),))
                        transaction.execute(
                            "INSERT INTO AuthSession(TokenHash,MaUser,ExpiresAt) VALUES(?,?,TIMESTAMPADD(HOUR,?,UTC_TIMESTAMP(3)))",
                            (digest(token), user["MaUser"], settings.session_hours),
                        )
                        _audit(transaction, user["MaUser"], "LOGIN_OTP", ip)
                    else:
                        user = None
        if not allowed:
            raise ApiError(429, "RATE_LIMITED")
        if user is None:
            raise ApiError(401, "OTP_INVALID")
        response.set_cookie(
            "vietincare_session", token, max_age=settings.session_hours * 3600,
            httponly=True, secure=settings.secure_cookie, samesite="strict", path="/",
        )
        return {"user": _public_user(user)}

    @app.get("/api/auth/me")
    def me(request: Request) -> dict[str, Any]:
        return {"user": _public_user(current_user(request, database))}

    @app.post("/api/auth/logout", status_code=204)
    def logout(request: Request, response: Response) -> Response:
        user = current_user(request, database)
        with database.transaction() as transaction:
            transaction.execute("DELETE FROM AuthSession WHERE TokenHash=?", (digest(user["_token"]),))
            _audit(transaction, user["MaUser"], "LOGOUT", request.client.host if request.client else None)
        response.delete_cookie("vietincare_session", path="/", secure=settings.secure_cookie, httponly=True, samesite="strict")
        response.status_code = 204
        return response

    @app.get("/api/customer/profile/{customer_id}")
    def profile(customer_id: str, request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Customer")
        if not customer_id.isdecimal() or int(customer_id) != user.get("MaKH"):
            raise ApiError(403, "FORBIDDEN")
        profile_data = database.fetch_one(
            "SELECT MaKH,HoTen,Email,SoDienThoai FROM Customer WHERE MaKH=? AND MaUser=?",
            (user["MaKH"], user["MaUser"]),
        )
        return {"profile": profile_data}

    @app.get("/api/workspace/{role}")
    def workspace(role: str, request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        if role != user["TenRole"]:
            raise ApiError(403, "FORBIDDEN")
        capabilities = {
            "Customer": {
                "implemented": ["authentication", "tickets", "chat", "handover"],
                "pending": ["chat-session-evaluation"],
            },
            "Agent": {
                "implemented": ["authentication", "tickets", "ticket-ai-assist", "handover", "chat-summary"],
                "pending": [],
            },
            "Supervisor": {
                "implemented": ["authentication", "tickets", "ticket-assignment", "reports", "handover", "chat-summary"],
                "pending": [],
            },
            "Admin": {
                "implemented": ["authentication", "user-management", "knowledge", "audit-log-search", "system-settings"],
                "pending": [],
            },
        }
        return {"user": _public_user(user), **capabilities[role]}

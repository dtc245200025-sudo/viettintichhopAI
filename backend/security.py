import hashlib
import hmac
import re
import secrets


_HASH_PATTERN = re.compile(r"^scrypt\$32768\$8\$1\$([a-f0-9]{32})\$([a-f0-9]{64})$")
_DUMMY_SALT = "00000000000000000000000000000000"


def digest(value: str | bytes) -> bytes:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).digest()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("ascii"), n=32768, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024)
    return f"scrypt$32768$8$1${salt}${key.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    match = _HASH_PATTERN.fullmatch(stored or "")
    salt = match.group(1) if match else _DUMMY_SALT
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("ascii"), n=32768, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024)
    return bool(match) and hmac.compare_digest(key, bytes.fromhex(match.group(2)))


def new_session_token() -> str:
    return secrets.token_hex(32)
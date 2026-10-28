from dataclasses import dataclass
import os
import re
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    origin: str
    secure_cookie: bool
    session_hours: int
    database: dict[str, object]
    ai_provider: str
    ai_key: str
    ai_chat_model: str
    ai_threshold: float = 0.35
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        values = os.environ if env is None else env

        def integer(name: str, default: int, low: int, high: int) -> int:
            raw = values.get(name, str(default))
            if not raw.isdecimal() or not low <= int(raw) <= high:
                raise ValueError(f"Invalid {name}")
            return int(raw)

        origin_url = urlparse(values.get("APP_ORIGIN", "http://localhost:3000"))
        if origin_url.scheme not in {"http", "https"} or not origin_url.hostname or origin_url.path not in {"", "/"} or origin_url.query or origin_url.fragment:
            raise ValueError("Invalid APP_ORIGIN")
        origin = f"{origin_url.scheme}://{origin_url.netloc}"
        secure = values.get("COOKIE_SECURE", "false").lower() == "true"
        if values.get("APP_ENV") == "production" and (not secure or origin_url.scheme != "https"):
            raise ValueError("Production requires HTTPS and secure cookies")

        database_name = values.get("DB_NAME", "QLKHViettin")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", database_name):
            raise ValueError("Invalid DB_NAME")
        provider = values.get("AI_PROVIDER") or ("gemini" if values.get("GEMINI_API_KEY") else "openai")
        if provider not in {"gemini", "openai"}:
            raise ValueError("Invalid AI_PROVIDER")
        ai_key_name = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
        model = values.get("GEMINI_CHAT_MODEL", "gemini-3.8-flash") if provider == "gemini" else values.get("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
        if provider == "gemini" and not re.fullmatch(r"[A-Za-z0-9._-]+", model):
            raise ValueError("Invalid GEMINI_CHAT_MODEL")

        return cls(
            host=values.get("HOST", "127.0.0.1"),
            port=integer("PORT", 3000, 1, 65535),
            origin=origin,
            secure_cookie=secure,
            session_hours=integer("SESSION_HOURS", 8, 1, 24),
            database={
                "host": values.get("DB_HOST", "127.0.0.1"),
                "port": integer("DB_PORT", 3306, 1, 65535),
                "user": values.get("DB_USER", "vietincare_app"),
                "password": values.get("DB_PASSWORD", ""),
                "database": database_name,
                "charset": "utf8mb4",
                "collation": "utf8mb4_0900_ai_ci",
                "time_zone": "+00:00",
                "connection_timeout": 5,
            },
            ai_provider=provider,
            ai_key=values.get(ai_key_name, ""),
            ai_chat_model=model,
            twilio_account_sid=values.get("TWILIO_ACCOUNT_SID", "").strip(),
            twilio_auth_token=values.get("TWILIO_AUTH_TOKEN", "").strip(),
            twilio_from_number=values.get("TWILIO_FROM_NUMBER", "").strip(),
        )

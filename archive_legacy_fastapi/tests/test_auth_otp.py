import httpx
import pytest
from contextlib import contextmanager
from fastapi.testclient import TestClient

from backend.auth import _e164_phone, _otp_hash
from backend.app import create_app
from backend.config import Settings
from backend.sms import TwilioSmsSender


def test_phone_normalization_accepts_vietnamese_local_and_international_formats() -> None:
    assert _e164_phone("0901 234 567") == "+84901234567"
    assert _e164_phone("+84 (901) 234-567") == "+84901234567"
    assert _e164_phone("+1 202 555 0100") == "+12025550100"
    assert _e164_phone("+0123456789") is None
    assert _e164_phone("not a phone") is None


def test_otp_hash_is_salted() -> None:
    salt_one = "01" * 16
    salt_two = "02" * 16
    assert _otp_hash(salt_one, "123456") != _otp_hash(salt_two, "123456")
    assert _otp_hash(salt_one, "123456") != _otp_hash(salt_one, "654321")


def test_twilio_sender_posts_otp_to_configured_phone_without_network() -> None:
    settings = Settings.from_env({
        "APP_ORIGIN": "http://localhost:3000",
        "TWILIO_ACCOUNT_SID": "AC" + "a" * 32,
        "TWILIO_AUTH_TOKEN": "test-token",
        "TWILIO_FROM_NUMBER": "+12025550100",
    })
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={"sid": "SM-test"})

    TwilioSmsSender(settings, httpx.MockTransport(respond)).send_otp("+84901234567", "123456")

    assert len(requests) == 1
    assert requests[0].url.host == "api.twilio.com"
    assert requests[0].url.path.endswith("/Messages.json")
    assert b"To=%2B84901234567" in requests[0].content
    assert b"123456" in requests[0].content


def test_twilio_sender_rejects_unconfigured_sms() -> None:
    sender = TwilioSmsSender(Settings.from_env({"APP_ORIGIN": "http://localhost:3000"}))

    with pytest.raises(RuntimeError, match="not configured"):
        sender.send_otp("+84901234567", "123456")


class FakeDatabase:
    def __init__(self) -> None:
        self.user_exists = True
        self.challenge: dict[str, object] | None = None
        self.user = {
            "MaUser": 7,
            "HoTen": "Test Customer",
            "Email": "customer@example.test",
            "TenRole": "Customer",
            "MaKH": 9,
            "CustomerActive": 1,
        }

    @contextmanager
    def transaction(self):
        yield self

    def fetch_one(self, statement: str, parameters: tuple[object, ...] = ()):
        if "SELECT Attempts,WindowEnd" in statement:
            return {"Attempts": 0, "expired": 1}
        if "SELECT MIN(u.MaUser) MaUser FROM UserAccount" in statement:
            return {"MaUser": 7} if self.user_exists else None
        if "SELECT MaChallenge,MaUser,CodeHash" in statement:
            return self.challenge
        if "SELECT u.*,r.TenRole,c.MaKH" in statement:
            return self.user
        return None

    def execute(self, statement: str, parameters: tuple[object, ...] = ()) -> int:
        if statement.startswith("INSERT INTO AuthOtpChallenge"):
            self.challenge = {
                "MaChallenge": 1,
                "MaUser": parameters[0],
                "CodeHash": parameters[2],
                "CodeSalt": parameters[3],
                "Attempts": 0,
                "Valid": 1,
            }
            return 1
        if statement.startswith("UPDATE AuthOtpChallenge SET Attempts") and self.challenge:
            self.challenge["Attempts"] = int(self.challenge["Attempts"]) + 1
        if statement.startswith("DELETE FROM AuthOtpChallenge"):
            self.challenge = None
        return 1


class FakeSmsSender:
    configured = True

    def __init__(self) -> None:
        self.code = ""

    def send_otp(self, phone: str, code: str) -> None:
        self.code = code


def test_otp_request_and_verification_create_a_session_only_after_valid_code() -> None:
    database = FakeDatabase()
    sms_sender = FakeSmsSender()
    settings = Settings.from_env({"APP_ORIGIN": "http://localhost:3000"})
    client = TestClient(create_app(database=database, settings=settings, sms_sender=sms_sender))
    headers = {"Origin": settings.origin, "X-Vietincare-Request": "1"}

    sent = client.post("/api/auth/otp/request", json={"phone": "0901 234 567"}, headers=headers)
    wrong = client.post("/api/auth/otp/verify", json={"phone": "0901 234 567", "code": "000000"}, headers=headers)

    assert sent.status_code == 200
    assert sent.json() == {"message": "OTP_SENT"}
    assert sms_sender.code != ""
    assert wrong.status_code == 401
    assert wrong.json() == {"error": "OTP_INVALID"}
    assert "vietincare_session" not in client.cookies

    verified = client.post("/api/auth/otp/verify", json={"phone": "0901 234 567", "code": sms_sender.code}, headers=headers)

    assert verified.status_code == 200
    assert verified.json()["user"]["id"] == 7
    assert "vietincare_session" in client.cookies
    assert database.challenge is None
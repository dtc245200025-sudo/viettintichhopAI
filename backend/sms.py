from collections.abc import Callable

import httpx

from backend.config import Settings


class TwilioSmsSender:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport

    @property
    def configured(self) -> bool:
        return all((self.settings.twilio_account_sid, self.settings.twilio_auth_token, self.settings.twilio_from_number))

    def send_otp(self, phone: str, code: str) -> None:
        if not self.configured:
            raise RuntimeError("SMS provider is not configured")
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.settings.twilio_account_sid}/Messages.json"
        message = f"Your VietinCare AI sign-in code is {code}. It expires in 5 minutes."
        try:
            with httpx.Client(timeout=10, follow_redirects=False, transport=self.transport) as client:
                response = client.post(
                    url,
                    auth=(self.settings.twilio_account_sid, self.settings.twilio_auth_token),
                    data={"To": phone, "From": self.settings.twilio_from_number, "Body": message},
                )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise RuntimeError("SMS delivery failed") from error
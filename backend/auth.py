"""
Telegram WebApp initData authentication.
Spec: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
from urllib.parse import unquote


def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """
    Validates the HMAC signature of Telegram WebApp initData.
    Returns the user dict on success, None on failure.
    """
    if not init_data or not bot_token:
        return None
    try:
        params: dict[str, str] = {}
        for part in init_data.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = unquote(v)

        received_hash = params.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(params.items())
        )

        # Secret key = HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()

        expected_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            return None

        return json.loads(params.get("user", "{}"))

    except Exception:
        return None

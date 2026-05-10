import hashlib
import hmac
import secrets


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def generate_api_key() -> str:
    return f"aps_{secrets.token_urlsafe(32)}"

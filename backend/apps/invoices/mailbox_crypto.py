"""Encrypt mailbox authorization codes with the app secret.

The ciphertext cannot be reversed without SECRET_KEY. Rotating SECRET_KEY
invalidates saved mailbox passwords and the user must authorize again.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise ValueError('邮箱授权码无法解密，请重新授权该邮箱。') from exc

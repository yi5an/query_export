import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import get_settings

_settings = get_settings()

# 从配置的密钥生成有效的 Fernet 密钥
_key = hashlib.sha256(_settings.app_secret_key.encode()).digest()
_fernet_key = base64.urlsafe_b64encode(_key)
_cipher = Fernet(_fernet_key)


def encrypt_password(password: str) -> str:
    """加密密码"""
    return _cipher.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """解密密码"""
    return _cipher.decrypt(encrypted.encode()).decode()
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings


def _fernet() -> Fernet:
    key = get_settings().one_encrypt_key
    if not key:
        raise RuntimeError(
            "ONE_ENCRYPT_KEY 未设置。请生成一个 Fernet 密钥并写入 .env：\n"
            '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode())


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("api_key 解密失败：ONE_ENCRYPT_KEY 与数据库中存储的密文不匹配") from exc


def mask(plaintext: str) -> str:
    if not plaintext:
        return ""
    if len(plaintext) <= 8:
        return "*" * len(plaintext)
    return plaintext[:4] + "*" * (len(plaintext) - 8) + plaintext[-4:]

"""
模块职能：
- 应用层加解密（账户密钥/会话数据），密文入库，明文只在内存中使用。
"""
import base64, json, os, hashlib
from cryptography.fernet import Fernet

def _derive_fernet_key(raw: str) -> bytes:
    h = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(h)

def _fernet() -> Fernet:
    secret = os.getenv("SECRET_KEY","dev-secret-change-me")
    return Fernet(_derive_fernet_key(secret))

def encrypt_dict(d: dict) -> str:
    return _fernet().encrypt(json.dumps(d).encode()).decode()

def decrypt_str(s: str) -> dict:
    return json.loads(_fernet().decrypt(s.encode()).decode())

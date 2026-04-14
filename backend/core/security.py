"""
Hachage et vérification des mots de passe (bcrypt).
"""
from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12, truncate_error=False)

def hash_password(password: str) -> str:
    return _ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return _ctx.verify(plain, hashed)

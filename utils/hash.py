from passlib.context import CryptContext


_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not is_password_hash(hashed_password):
        return False
    return _pwd_context.verify(plain_password, hashed_password)


def is_password_hash(value: str) -> bool:
    try:
        return _pwd_context.identify(value) is not None
    except Exception:
        return False

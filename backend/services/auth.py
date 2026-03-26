from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_TYP_ACCESS = "access"
JWT_TYP_REFRESH = "refresh"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(subject: int | str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "typ": JWT_TYP_ACCESS,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: int | str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "typ": JWT_TYP_REFRESH,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    credentials_error = _credentials_error()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise credentials_error from exc
    if payload.get("typ") != JWT_TYP_ACCESS:
        raise credentials_error
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise credentials_error from exc
    if payload.get("typ") != JWT_TYP_REFRESH:
        raise credentials_error
    return payload

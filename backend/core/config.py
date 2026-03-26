from functools import lru_cache
import os


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./hibou.db")
        self.jwt_secret = os.getenv(
            "JWT_SECRET",
            "change-me-in-production-with-a-random-secret",
        )
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        )
        self.refresh_token_expire_days = int(
            os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
        )
        self.refresh_token_cookie_name = os.getenv(
            "REFRESH_TOKEN_COOKIE_NAME",
            "refresh_token",
        )
        self.cookie_secure = os.getenv("COOKIE_SECURE", "").lower() in (
            "1",
            "true",
            "yes",
        )
        raw_samesite = os.getenv("COOKIE_SAMESITE", "lax").lower()
        if raw_samesite not in ("lax", "strict", "none"):
            raw_samesite = "lax"
        self.cookie_samesite: str = raw_samesite
        self.frontend_origins = tuple(
            origin.strip()
            for origin in os.getenv(
                "FRONTEND_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        )
        self.zmq_sub_string = os.getenv("ZMQ_SUB_STRING", "tcp://127.0.0.1:5557")
        self.zmq_pub_string = os.getenv("ZMQ_PUB_STRING", "tcp://127.0.0.1:5556")


@lru_cache
def get_settings() -> Settings:
    return Settings()

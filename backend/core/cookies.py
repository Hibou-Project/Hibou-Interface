from starlette.responses import Response

from core.config import get_settings


def attach_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    max_age = settings.refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from core.config import get_settings
from core.cookies import attach_refresh_cookie, clear_refresh_cookie
from core.dependencies import bearer_scheme, get_current_user, get_db
from models import User
from services.auth import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)

router = APIRouter()


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    result = await db.execute(select(User).where(User.identifier == payload.identifier))
    existing_user = result.scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Identifier is already taken",
        )

    user = User(
        identifier=payload.identifier,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    result = await db.execute(select(User).where(User.identifier == payload.identifier))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid identifier or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    body = TokenResponse(
        access_token=access_token,
        user=UserPublic.model_validate(user),
    )
    response = JSONResponse(content=body.model_dump(mode="json"))
    attach_refresh_cookie(response, refresh_token)
    print("attached refresh cookie")
    return response


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(request: Request, db: AsyncSession = Depends(get_db)) -> AccessTokenResponse:
    settings = get_settings()
    raw = request.cookies.get(settings.refresh_token_cookie_name)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    payload = decode_refresh_token(raw)
    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    try:
        user_id = int(user_id_raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    access_token = create_access_token(user.id)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    clear_refresh_cookie(response)
    return {}


@router.get(
    "/me",
    response_model=UserPublic,
    dependencies=[Security(bearer_scheme)],
)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user

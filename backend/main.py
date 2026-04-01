from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.events import router as events_router
from api.settings import router as settings_router
from api.video import router as video_router
from core.config import get_settings
from core.lifespan import lifespan


def create_app() -> FastAPI:
    _app = FastAPI(
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True},
    )
    settings = get_settings()

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.frontend_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _app.include_router(auth_router, prefix="/auth", tags=["auth"])
    _app.include_router(events_router, prefix="/events", tags=["events"])
    _app.include_router(settings_router, prefix="/settings", tags=["settings"])
    _app.include_router(video_router, prefix="/video", tags=["video"])
    return _app


app = create_app()
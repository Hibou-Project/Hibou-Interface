import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.config import get_settings
from core.db import create_engine_and_session_factory, sqlite_add_missing_columns
from models import Base
from services.ipc_forwarder.zeromq import ZMQForwarder
from services.vision_stream import VisionMjpegSource, run_vision_zmq_ingest


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine, session_factory = create_engine_and_session_factory(settings.database_url)
    app.state.db_engine = engine
    app.state.session_factory = session_factory

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(sqlite_add_missing_columns)

    """
    Start ZeroMQ sockets forwarder and vision video ingest (MJPEG sources).
    """
    app.state.vision_mjpeg_raw = VisionMjpegSource()
    app.state.vision_mjpeg_annotated = VisionMjpegSource()
    vision_stop = asyncio.Event()
    broadcast_task = asyncio.create_task(ZMQForwarder().forwarder())
    vision_tasks = [
        asyncio.create_task(
            run_vision_zmq_ingest(
                settings.vision_zmq_raw,
                app.state.vision_mjpeg_raw,
                vision_stop,
            )
        ),
        asyncio.create_task(
            run_vision_zmq_ingest(
                settings.vision_zmq_annotated,
                app.state.vision_mjpeg_annotated,
                vision_stop,
            )
        ),
    ]

    try:
        yield
    finally:
        vision_stop.set()
        broadcast_task.cancel()
        for vt in vision_tasks:
            vt.cancel()
        await asyncio.gather(
            broadcast_task,
            *vision_tasks,
            return_exceptions=True,
        )
        await engine.dispose()
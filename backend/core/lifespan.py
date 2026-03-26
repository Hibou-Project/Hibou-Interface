import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.datastructures import State
import zmq
import zmq.asyncio
import json

from core.config import get_settings
from core.db import create_engine_and_session_factory
from models import Base
from services.ipc_forwarder.zeromq import ZMQForwarder

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine, session_factory = create_engine_and_session_factory(settings.database_url)
    app.state.db_engine = engine
    app.state.session_factory = session_factory

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    """
    Start ZeroMQ sockets forwarder
    """
    broadcast_task = asyncio.create_task(ZMQForwarder().forwarder())

    try:
        yield
    finally:
        broadcast_task.cancel()
        await asyncio.gather(broadcast_task, return_exceptions=True)
        await engine.dispose()
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from core.dependencies import get_current_user_websocket
from models import User
from services.ipc_forwarder.zeromq import ZMQForwarder

router = APIRouter()


class ConnectionManager:
    def __init__(self, ipc: ZMQForwarder):
        self.clients: list[WebSocket] = []
        self.ipc_forwarder = ipc

    async def connect(self, ws: WebSocket):
        self.clients.append(ws)

        # Start listening for messages from the client and relay them to the IPC forwarder
        while True:
            try:
                data = await ws.receive_text()
                await self.send_over_ipc(data)
            except WebSocketDisconnect:
                self.disconnect(ws)
                break

    def disconnect(self, ws: WebSocket):
        self.clients.remove(ws)

    async def broadcast(self, message: str):
        for client in list(self.clients):
            try:
                await client.send_text(message)
            except Exception:
                self.disconnect(client)

    async def send_over_ipc(self, message: str):
        await self.ipc_forwarder.publish(message)

websocket_manager = ConnectionManager(ipc=ZMQForwarder())


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    _user: Annotated[User, Depends(get_current_user_websocket)],
):
    await ws.accept()
    await websocket_manager.connect(ws)
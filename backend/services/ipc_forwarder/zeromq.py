import zmq.asyncio
import asyncio
import json
from core.config import get_settings
from helpers.decorators import singleton

@singleton
class ZMQForwarder:
    """
    Simple ZMQ Forwarder.
    """
    def __init__(self):
        context = zmq.asyncio.Context()
        settings = get_settings()

        self.pub_socket = None
        pub_socket = context.socket(zmq.PUB)
        pub_socket.connect(settings.zmq_pub_string)
        self.pub = pub_socket

        sub_socket = context.socket(zmq.SUB)
        sub_socket.connect(settings.zmq_sub_string)
        self.sub = sub_socket

    async def forwarder(self):
        from api.events import websocket_manager

        self.sub.setsockopt(zmq.SUBSCRIBE, b"")
        while True:
            try:
                data = (await self.sub.recv_multipart())[0].decode()
                await websocket_manager.broadcast(data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[broadcaster] error: {e}")

    def publish(self, message: str):
        print(f"[ZMQForwarder] Publishing message: {message}")
        self.pub.send(message.encode())



"""
ZMQ SUB ingest: unpickle trusted send_pyobj frames, normalize to JPEG for MJPEG streaming.

SUB connects to the vision process PUB bind address. Unpickling untrusted peers is unsafe.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np
import zmq.asyncio

logger = logging.getLogger(__name__)

_MAX_DEPTH = 6
_DICT_KEYS = ("frame", "image", "img", "array", "data", "bgr", "rgb")
_JPEG = (int(cv2.IMWRITE_JPEG_QUALITY), 85)


def _is_frame_candidate(x: Any) -> bool:
    if isinstance(x, (bytes, bytearray, memoryview)):
        return True
    if isinstance(x, np.ndarray) and x.ndim >= 2:
        return True
    if type(x).__name__ == "Tensor" and hasattr(x, "detach"):
        return True
    return hasattr(x, "__array__")


def _unwrap(x: Any, depth: int = 0) -> Any:
    if x is None or depth > _MAX_DEPTH:
        return x
    if isinstance(x, dict):
        for k in _DICT_KEYS:
            if k in x:
                return _unwrap(x[k], depth + 1)
        for v in x.values():
            if _is_frame_candidate(v):
                return _unwrap(v, depth + 1)
        return x
    if isinstance(x, (tuple, list)):
        if not x:
            return x
        for item in x:
            if _is_frame_candidate(item):
                return _unwrap(item, depth + 1)
        return _unwrap(x[0], depth + 1)
    return x


def _tensor_as_ndarray(obj: Any) -> np.ndarray | None:
    if type(obj).__name__ != "Tensor" or not hasattr(obj, "detach"):
        return None
    try:
        arr = obj.detach().cpu().numpy()
        return arr if isinstance(arr, np.ndarray) else None
    except Exception:
        return None


def _as_uint8_hw(nd: np.ndarray) -> np.ndarray | None:
    if nd.ndim < 2:
        return None
    if nd.dtype == np.uint8:
        out = nd
    elif nd.dtype in (np.float32, np.float64):
        hi = float(nd.max()) if nd.size else 0.0
        if hi <= 1.0:
            out = (np.clip(nd, 0.0, 1.0) * 255.0).astype(np.uint8)
        else:
            out = np.clip(nd, 0.0, 255.0).astype(np.uint8)
    else:
        out = np.asarray(nd, dtype=np.uint8)
    return np.ascontiguousarray(out)


def message_to_jpeg(message: Any) -> bytes | None:
    """Turn one recv_pyobj payload into JPEG bytes, or None if unsupported."""
    if message is None:
        return None
    core = _unwrap(message)

    if isinstance(core, (bytes, bytearray, memoryview)):
        return bytes(core)

    arr: np.ndarray | None = _tensor_as_ndarray(core)
    if arr is None and hasattr(core, "__array__") and not isinstance(core, np.ndarray):
        try:
            arr = np.asarray(core)
        except (TypeError, ValueError):
            arr = None
    elif arr is None and isinstance(core, np.ndarray):
        arr = core

    if not isinstance(arr, np.ndarray):
        return None

    image = _as_uint8_hw(arr)
    if image is None:
        return None
    try:
        ok, buf = cv2.imencode(".jpg", image, _JPEG)
    except cv2.error:
        return None
    if not ok:
        return None
    return buf.tobytes()


@dataclass
class VisionMjpegSource:
    """
    Shared latest JPEG + monotonic generation so each HTTP client streams new frames
    without a single shared asyncio.Queue stealing messages from other clients.
    """

    first_frame: asyncio.Event = field(default_factory=asyncio.Event)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _ready: asyncio.Condition = field(init=False)
    _jpeg: bytes | None = field(default=None, init=False)
    _gen: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_ready", asyncio.Condition(self._lock))

    async def publish_jpeg(self, jpeg: bytes) -> None:
        async with self._ready:
            self._jpeg = jpeg
            self._gen += 1
            self.first_frame.set()
            self._ready.notify_all()

    async def wait_next_jpeg(self, seen_gen: int) -> tuple[bytes, int]:
        async with self._ready:
            while self._jpeg is None or self._gen <= seen_gen:
                await self._ready.wait()
            assert self._jpeg is not None
            return self._jpeg, self._gen


async def run_vision_zmq_ingest(
    endpoint: str,
    source: VisionMjpegSource,
    stop: asyncio.Event,
) -> None:
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(zmq.SUB)
    sock.setsockopt(zmq.SUBSCRIBE, b"")
    sock.connect(endpoint)
    await asyncio.sleep(0.2)
    try:
        while not stop.is_set():
            try:
                obj = await asyncio.wait_for(sock.recv_pyobj(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            jpeg = message_to_jpeg(obj)
            if jpeg:
                await source.publish_jpeg(jpeg)
            else:
                logger.warning(
                    "vision_zmq %s: got %s, could not build JPEG",
                    endpoint,
                    type(obj).__name__,
                )
    except asyncio.CancelledError:
        raise
    finally:
        sock.close(linger=0)
        ctx.term()

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from core.dependencies import get_current_user_media
from models import User
from services.vision_stream.ingest import VisionMjpegSource

router = APIRouter()

_MJPEG_HDR = b"--ffmpeg\r\nContent-Type: image/jpeg\r\n\r\n"


@router.get(
    "/ptz/mjpeg",
    summary="Live camera (ZMQ vision frames as MJPEG for browsers)",
)
async def ptz_mjpeg_stream(
    request: Request,
    channel: Annotated[
        Literal["raw", "annotated"],
        Query(description="ZMQ stream: raw or annotated publisher"),
    ] = "annotated",
    _user: User = Depends(get_current_user_media),
) -> StreamingResponse:
    raw_src = request.app.state.vision_mjpeg_raw
    ann_src = request.app.state.vision_mjpeg_annotated
    src: VisionMjpegSource = raw_src if channel == "raw" else ann_src

    try:
        await asyncio.wait_for(src.first_frame.wait(), timeout=5.0)
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Error fetching video stream"
            ),
        ) from None

    async def generate() -> AsyncIterator[bytes]:
        seen_gen = -1
        try:
            while True:
                jpeg, seen_gen = await src.wait_next_jpeg(seen_gen)
                yield _MJPEG_HDR + jpeg + b"\r\n"
        except asyncio.CancelledError:
            raise

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace;boundary=ffmpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )

import asyncio
import logging
import typing

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from .processor import processor

logger = logging.getLogger("LiveServer")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")  # type: ignore
async def startup_event() -> None:
    # Pass the running loop to the processor
    loop = asyncio.get_running_loop()
    processor.start(loop)


@app.on_event("shutdown")  # type: ignore
async def shutdown_event() -> None:
    processor.stop()


@app.get("/")  # type: ignore
async def get() -> HTMLResponse:
    return HTMLResponse("<h1>Silvasonic Brain Live</h1><p>Active.</p>")


@app.websocket("/ws/spectrogram")  # type: ignore
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.debug("WS Connected")

    queue = await processor.subscribe_spectrogram()

    try:
        while True:
            # Wait for new frame
            data = await queue.get()

            # Send binary or json
            await websocket.send_json({"type": "spectrogram", "data": data})

    except WebSocketDisconnect:
        logger.debug("WS Disconnected")
    finally:
        processor.unsubscribe_spectrogram(queue)


@app.get("/stream")  # type: ignore
async def stream_audio() -> StreamingResponse:
    """Streams audio to the browser by piping the creation of MP3."""
    return StreamingResponse(
        audio_stream_generator(), media_type="audio/mpeg", headers={"Cache-Control": "no-cache"}
    )


async def audio_stream_generator() -> typing.AsyncGenerator[bytes, None]:
    """1. Subscribes to Raw Audio Queue.
    2. Spawns FFmpeg process (Async).
    3. Writes Queue Data -> FFmpeg Stdin (Background Task).
    4. Reads FFmpeg Stdout -> Buffer -> Yield.
    """
    # FFmpeg command: Read PCM from Pipe, Write MP3 to Pipe
    cmd = [
        "ffmpeg",
        "-f",
        "s16le",  # Input format: Signed 16-bit Little Endian
        "-ar",
        "48000",  # Input Sample Rate
        "-ac",
        "1",  # Input Channels
        "-i",
        "pipe:0",  # Input from Stdin
        "-f",
        "mp3",  # Output format
        "-b:a",
        "128k",  # Bitrate
        "-ar",
        "44100",  # Output Sample Rate (Standard for Web)
        "pipe:1",  # Output to Stdout
    ]

    # Create async subprocess
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,  # Silence logs
    )

    if not proc.stdin or not proc.stdout:
        logger.error("Failed to start FFmpeg process pipes")
        if proc.returncode is None:
            proc.kill()
        return

    queue = await processor.subscribe_audio()

    # Start background task to feed input to FFmpeg
    input_task = asyncio.create_task(feed_input(proc.stdin, queue))

    try:
        while True:
            # Read output (Async non-blocking)
            out_data = await proc.stdout.read(4096)
            if not out_data:
                break
            yield out_data

    except Exception as e:
        logger.error(f"Stream Error: {e}")
    finally:
        # Cleanup
        input_task.cancel()
        processor.unsubscribe_audio(queue)

        try:
            proc.terminate()
            await proc.wait()
        except Exception:
            pass


async def feed_input(stdin_writer: asyncio.StreamWriter, queue: asyncio.Queue[bytes]) -> None:
    """Feeds audio chunks from queue to FFmpeg stdin"""
    try:
        while True:
            chunk = await queue.get()
            stdin_writer.write(chunk)
            await stdin_writer.drain()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Feed Input Error: {e}")

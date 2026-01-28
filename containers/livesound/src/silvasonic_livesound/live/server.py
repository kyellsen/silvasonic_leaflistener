import asyncio
import logging
import typing
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from .models import SourceConfig, SourceStatus
from .processor import processor

logger = logging.getLogger("LiveServer")


@asynccontextmanager
async def lifespan(app: FastAPI) -> typing.AsyncGenerator[None, None]:
    # Startup: Pass the running loop to the processor
    loop = asyncio.get_running_loop()
    processor.start(loop)
    yield
    # Shutdown
    processor.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def get() -> HTMLResponse:
    return HTMLResponse("<h1>Silvasonic LiveSound</h1><p>Active.</p>")


# --- User-Centric API (Option C) ---


@app.get("/sources", response_model=list[SourceStatus])
async def list_sources() -> list[SourceStatus]:
    """Get active audio sources and their live signal health."""
    return processor.get_source_stats()


@app.post("/sources")
async def add_source(config: SourceConfig) -> dict[str, str]:
    """Add a new audio source dynamically."""
    processor.add_source(config.name, config.port)
    return {"status": "added", "name": config.name}


@app.delete("/sources/{name}")
async def remove_source(name: str) -> dict[str, str]:
    """Remove an audio source."""
    processor.remove_source(name)
    return {"status": "removed", "name": name}


# --- Streaming Endpoints ---


@app.websocket("/ws/spectrogram")
async def websocket_endpoint(websocket: WebSocket, source: str = "default") -> None:
    """WebSocket endpoint for spectrogram data.
    Usage: ws://host/ws/spectrogram?source=front
    """
    await websocket.accept()
    logger.debug(f"WS Connected [Source: {source}]")

    queue = await processor.subscribe_spectrogram(source)

    try:
        while True:
            # Wait for new frame
            data = await queue.get()

            # Send binary (orjson already returned bytes)
            # We send the raw bytes directly to ensure maximum performance.
            await websocket.send_bytes(data)

    except WebSocketDisconnect:
        logger.debug("WS Disconnected")
    finally:
        processor.unsubscribe_spectrogram(queue, source)


@app.get("/stream")
async def stream_audio(source: str = "default") -> StreamingResponse:
    """Streams audio to the browser by piping the creation of MP3.
    Usage: GET /stream?source=front
    """
    return StreamingResponse(
        audio_stream_generator(source),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-cache"},
    )


async def audio_stream_generator(source: str) -> typing.AsyncGenerator[bytes, None]:
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

    queue = await processor.subscribe_audio(source)

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
        processor.unsubscribe_audio(queue, source)

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

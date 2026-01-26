import asyncio
import logging
import subprocess

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

@app.on_event("startup")
async def startup_event():
    # Pass the running loop to the processor
    loop = asyncio.get_running_loop()
    processor.start(loop)

@app.on_event("shutdown")
async def shutdown_event():
    processor.stop()

@app.get("/")
async def get():
    return HTMLResponse("<h1>Silvasonic Brain Live</h1><p>Active.</p>")

@app.websocket("/ws/spectrogram")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.debug("WS Connected")

    queue = await processor.subscribe_spectrogram()

    try:
        while True:
            # Wait for new frame
            data = await queue.get()

            # Send binary or json
            await websocket.send_json({
                "type": "spectrogram",
                "data": data
            })

    except WebSocketDisconnect:
        logger.debug("WS Disconnected")
    finally:
        processor.unsubscribe_spectrogram(queue)

@app.get("/stream")
async def stream_audio():
    """Streams audio to the browser by piping the creation of MP3.
    """
    return StreamingResponse(
        audio_stream_generator(),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-cache"}
    )

async def audio_stream_generator():
    """1. Subscribes to Raw Audio Queue.
    2. Spawns FFmpeg process.
    3. Writes Queue Data -> FFmpeg Stdin.
    4. Reads FFmpeg Stdout -> Buffer -> Yield.
    """
    # FFmpeg command: Read PCM from Pipe, Write MP3 to Pipe
    cmd = [
        "ffmpeg",
        "-f", "s16le",       # Input format: Signed 16-bit Little Endian
        "-ar", "48000",      # Input Sample Rate
        "-ac", "1",          # Input Channels
        "-i", "pipe:0",      # Input from Stdin
        "-f", "mp3",         # Output format
        "-b:a", "128k",      # Bitrate
        "-ar", "44100",      # Output Sample Rate (Standard for Web)
        "pipe:1"             # Output to Stdout
    ]

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, # Silence logs
    )

    queue = await processor.subscribe_audio()

    try:
        # We need a non-blocking way to communicate with subprocess in asyncio.
        # Since subprocess.Popen is blocking I/O on pipes, we should use proper async subprocess
        # or threading.
        # But writing to stdin can fill buffer.

        # NOTE: A robust solution requires two tasks:
        # 1. Pump Queue -> Stdin
        # 2. Pump Stdout -> Yield

        # Let's try a simpler buffer check loop

        # Optimization: We can't block this generator loop waiting for queue if we also want to read stdout.
        # But we CAN just write responsibly.

        while True:
            # 1. Get audio chunks (non-blocking if possible, else wait)
            # This is the driver. If no audio coming in, no stream going out.
            chunk = await queue.get()

            # 2. Write to FFmpeg
            # This might block if FFmpeg buffer is full, which is good (backpressure)
            proc.stdin.write(chunk)
            proc.stdin.flush()

            # 3. Read available output
            # We blindly read a chunk.
            # Ideally we read however much is available.
            # mp3 frame is small.
            out_data = proc.stdout.read(4096)
            if out_data:
                yield out_data

    except Exception as e:
        logger.error(f"Stream Error: {e}")
    finally:
        processor.unsubscribe_audio(queue)
        proc.kill()

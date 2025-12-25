from fastapi import FastAPI, Response
from silero import silero_tts
from contextlib import asynccontextmanager
from typing import List, Optional
import torch
import io
import soundfile as sf


@asynccontextmanager
async def lifespan(app: FastAPI):
    device = torch.device("cpu")
    app.state.model, _ = silero_tts(language='ru', speaker='v4_ru')
    app.state.model.to(device)
    yield

app = FastAPI(
    title="TTS Module",
    description="Responsible for work with Silero",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/synthesize")
async def synthesize(text: str, speaker:str = "aidar", sample_rate: int = 48000):
    audio = app.state.model.apply_tts (
        text = text,
        speaker = speaker,
        sample_rate = sample_rate
    )

    au_np = audio.numpy()

    buffer = io.BytesIO()

    sf.write(buffer, au_np, 48000, format='WAV')

    return Response(content=buffer.getvalue(), media_type="audio/wav")





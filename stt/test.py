from fastapi import FastAPI, UploadFile, HTTPException
from contextlib import asynccontextmanager
import whisper, os, tempfile

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = whisper.load_model("small")
    a: whisper.Whisper = app.state.model

    a.transcribe
    yield


app = FastAPI(
    title="Whisper app",
    description="Used for transcribing audio",
    version="1.0.0",
    lifespan=lifespan
)



@app.get("/test")
def test():
    model = app.state.model
    return { "answer" :  model.transcribe("test.m4a", language="ru") }

@app.post("/upload-transcribe-audio")
async def upload_audio(file: UploadFile):

    if not file.content_type or not file.content_type.startswith("audio"):
        raise HTTPException(400, "Неизвестный тип файла")

    model = app.state.model
    audio_bytes = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wax") as buffer:
        buffer.write(audio_bytes)
        tmp_path = buffer.name

    try:
        model = app.state.model
        result = model.transcribe(tmp_path, language="ru")
        return result

    finally:
        os.unlink(tmp_path)
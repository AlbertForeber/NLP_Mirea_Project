FROM python:3.13-slim

WORKDIR /app
COPY tts_fastapi.py  .
COPY latest_silero_models.yml .
COPY requirements.txt .

RUN pip install --upgrade pip
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    torch==2.6.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu


#RUN pip install --no-cache-dir --no-cache-dir torch  --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
CMD ["uvicorn",  "tts_fastapi:app", "--host", "0.0.0.0", "--port", "8001"]
# Using latest python version in 3.10
FROM python:3.10.11-bullseye

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install Whisper
RUN pip install git+https://github.com/openai/whisper.git

COPY ./requirements.txt ./test.py ./
COPY ./whisper_model /root/.cache/whisper/

RUN pip install --no-cache-dir -r requirements.txt

# Install model files so they don't download each time
RUN whisper --model small dummy.wav; exit 0

CMD ["uvicorn", "test:app", "--host",  "0.0.0.0", "--port", "8002"]
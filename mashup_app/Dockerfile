# Container image for the Mashup Maker web app.
# Works on Render, Railway, Fly.io, or plain `docker run`.
FROM python:3.11-slim

# ffmpeg is required by pydub to read/write MP3, OGG, etc.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Uploaded sources and generated mashups (ephemeral on most hosts).
RUN mkdir -p uploads outputs

EXPOSE 8000

# Long timeout: time-stretching a full song can take a while.
# Shell form so $PORT (injected by the host) is expanded at runtime.
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 300

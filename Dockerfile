FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Upgrade pip and pull CPU-only TF from Google index
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://storage.googleapis.com/tensorflow/linux/cpu

COPY . .

ENV PORT=8080
EXPOSE $PORT

CMD ["sh", "-c", "exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app"]

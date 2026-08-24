# Alice — container image for Hugging Face Spaces, Fly.io, Koyeb, Cloud Run…
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ALICE_DATA_DIR=/data

# Hugging Face runs containers as an unprivileged user.
RUN useradd -m -u 1000 alice

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Writable home for memory, reminders, notes and artifacts.
RUN mkdir -p /data && chown -R alice:alice /data /app

USER alice

# HF Spaces expects 0.0.0.0:7860; other hosts inject PORT.
ENV ALICE_PORT=7860
EXPOSE 7860

CMD ["python", "-m", "server"]

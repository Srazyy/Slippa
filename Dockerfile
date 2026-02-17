# ── Build stage ──────────────────────────────────────────
FROM python:3.11-slim AS base

# System deps: ffmpeg for video processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK / TextBlob corpora at build time
RUN python -c "\
import ssl; ssl._create_default_https_context = ssl._create_unverified_context; \
import nltk; \
nltk.download('punkt_tab', quiet=True); \
nltk.download('brown', quiet=True); \
nltk.download('conll2000', quiet=True); \
nltk.download('movie_reviews', quiet=True); \
nltk.download('averaged_perceptron_tagger_eng', quiet=True)"

# Copy application code
COPY . .

# Create dirs for runtime data
RUN mkdir -p clips downloads

# Expose Flask port
EXPOSE 5000

# Run the web UI
CMD ["python", "-m", "slippa"]

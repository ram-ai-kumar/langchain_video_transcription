# Use Python 3.11 slim as the base image
FROM python:3.11-slim

# Set environment variables to non-interactive to avoid prompts during apt-get
ENV DEBIAN_FRONTEND=noninteractive
# Set Python to run unbuffered for immediate log output
ENV PYTHONUNBUFFERED=1

# Install system dependencies
# ffmpeg: required for audio extraction
# tesseract-ocr: required for OCR features
# pandoc: required for document conversion/PDF generation
# curl, wget, ca-certificates: required for downloading tectonic and other network operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tesseract-ocr \
    pandoc \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install tectonic
# The installer script fails for arm64 linux currently, so we download the release directly
RUN if [ "$(uname -m)" = "aarch64" ]; then \
    curl -L "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/tectonic-0.15.0-aarch64-unknown-linux-musl.tar.gz" | tar xz -C /usr/local/bin; \
    else \
    curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh && mv tectonic /usr/local/bin/; \
    fi

# Set the working directory
WORKDIR /app

# Copy requirement files first for better caching
COPY requirements.txt requirements.in ./

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Ensure the entrypoint has execution permissions
RUN chmod +x main.py

# Define the entrypoint
ENTRYPOINT ["python", "main.py"]

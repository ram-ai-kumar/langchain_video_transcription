# Step-by-Step Setup

[← Back to README](../README.md)

## Option 1: Using mise (Recommended)

1. **Clone the repository**

   ```bash
   git clone <this-repo-url> video_transcription
   cd video_transcription
   ```

2. **Install mise** (if not already installed)
   - Follow instructions at [https://mise.jdx.dev/](https://mise.jdx.dev/)

3. **Install Python and dependencies with mise**

   ```bash
   mise install
   pip install -r requirements.txt
   ```

## Option 2: Manual Setup

1. **Clone the repository**

   ```bash
   git clone <this-repo-url> video_transcription
   cd video_transcription
   ```

2. **Create and activate a virtual environment**

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install system tools** (if not already installed)
   - Install `ffmpeg`, `tesseract`, and `pandoc` + a LaTeX distribution using the commands in [Prerequisites](PREREQUISITES.md).

5. **Prepare Ollama**
   - Install Ollama and start the Ollama service.
   - Pull the model the script uses (default is `gemma3`):

   ```bash
   ollama pull gemma3
   ```

## Option 3: Docker (Zero-Install)

If you don't want to install system prerequisites like `ffmpeg` or manage Python virtual environments, you can use the provided Docker setup.

1. **Clone the repository**

   ```bash
   git clone <this-repo-url> video_transcription
   cd video_transcription
   ```

2. **Ensure Ollama is running**
   - The container expects Ollama to be available on your host machine to leverage local hardware.
   - Make sure you've pulled your desired model: `ollama pull gemma3`

3. **Run the pipeline**
   - The Docker Compose configuration automatically mounts your local directory so the project can access media files and output results inside the current folder.

   ```bash
   docker compose run --rm transcriber /data/your-media-file.mp4
   ```

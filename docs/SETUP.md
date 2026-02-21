# Step-by-Step Setup

[← Back to README](../README.md)

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

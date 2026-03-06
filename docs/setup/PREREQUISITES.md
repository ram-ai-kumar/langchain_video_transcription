# Prerequisites

[← Back to README](../README.md)

- **Python**: 3.11 or newer
- **ffmpeg**: for video → audio extraction
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
- **Tesseract OCR**: for image processing
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
- **Pandoc + Tectonic** (only if you want PDFs)
  - macOS: `brew install pandoc tectonic`
  - Ubuntu/Debian: `sudo apt-get install pandoc` and install Tectonic from https://tectonic-typesetting.github.io/
- **Ollama** with an LLM model (defaults to `gemma3`)
  - Install Ollama from their website
  - Pull a model, for example: `ollama pull gemma3`

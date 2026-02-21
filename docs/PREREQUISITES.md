# Prerequisites

[← Back to README](../README.md)

- **Python**: 3.11 or newer
- **ffmpeg**: for video → audio extraction
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
- **Tesseract OCR**: for image processing
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
- **Pandoc + LaTeX** (only if you want PDFs)
  - macOS: `brew install pandoc mactex` (or any full LaTeX distro)
  - Ubuntu/Debian: `sudo apt-get install pandoc texlive-latex-recommended`
- **XeLaTeX** (recommended for Unicode support)
  - Usually included with modern LaTeX distributions
- **Ollama** with an LLM model (defaults to `gemma3`)
  - Install Ollama from their website
  - Pull a model, for example: `ollama pull gemma3`

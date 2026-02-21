# Features

[← Back to README](../README.md)

- **Unified Mixed Media Processing**: Processes **video, audio, text, and images** simultaneously in the same folder with intelligent conflict resolution.
- **Recursive Processing**: Scans entire directory subtree and processes files in every folder.
- **Deterministic Ordering**: Visits folders, files, and filename groups in **chronological/lexicographic ascending order by name** (case-insensitive) so runs are repeatable and easy to reason about.
- **Multi-Source Entry**: Start from **Video**, **Audio**, **Text**, or **Images** with smart precedence handling.
- **Video → Audio Extraction**: Uses `ffmpeg` to isolate audio streams from video files (skipped if starting from audio).
- **Audio → Transcript**: Employs [OpenAI Whisper](https://github.com/openai/whisper) for accurate speech-to-text transcription (skipped if starting from text).
- **Images → OCR**: Uses Tesseract OCR to extract text from images, supporting both grouped and loose image processing.
- **Transcript → Study Chapter**: Leverages [LangChain](https://www.langchain.com/) with Ollama LLM models to generate a **standalone textbook-style chapter** (not just a summary) based on discovered topics.
- **Rich Study Material Structure**:
  - Learning objectives
  - Executive overview
  - Core concepts and precise definitions
  - In-depth coverage with best practices and pitfalls
  - Glossary of important terms
  - Practice questions (MCQ, short answer, and critical thinking)
- **Externalized Study Prompt**: Define the textbook author persona, structure, and rules in `config/study_prompt.txt` for easy customization.
- **Enhanced PDF Generation**: Multi-engine PDF generation with XeLaTeX (Unicode support) → pdfLaTeX (enhanced) → Minimal fallback.
- **Unicode Support**: Handles Greek letters, special characters, and international symbols in PDFs.
- **Smart File Naming**: Conflict-aware naming for mixed media (`{stem}_images.txt` for conflicts, `{stem}.txt` for clean cases).
- **CLI Experience**: Clean, readable progress updates with dynamic pipeline paths and spinners.
- **Robust Error Handling**: Graceful fallbacks and detailed error reporting for PDF generation issues.

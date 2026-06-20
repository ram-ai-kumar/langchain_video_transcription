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
- **Enhanced PDF Generation**: PDF generation using Tectonic (XeTeX-based, with native Unicode support) → Minimal fallback.
- **Standard Footer**: Developer attribution and "AI-generated" content notice in PDF footers.
- **Unicode Support**: Handles Greek letters, special characters, and international symbols in PDFs.
- **Docker Support (Zero-Install)**: Run the pipeline via a clean Docker container, eliminating the need to install host dependencies like `ffmpeg`, `tesseract`, or `pandoc`.
- **Optimized Resource Usage**: Models (Whisper and Ollama) are strictly lazy-loaded into VRAM only at the exact moment their specific processing tasks (e.g. audio transcription or chapter generation) begin.
- **Smart File Naming**: Conflict-aware naming for mixed media (`{stem}_images.txt` for conflicts, `{stem}.txt` for clean cases).
- **Sequential Processing**: Files are processed one-by-one in deterministic order for maximum reliability and predictable resource usage.
- **Target-Based Pipeline**: Stop at any stage with `--target audio/text/markdown/pdf` for efficient processing.
- **Interactive CLI**: Prompts for desired output target when not specified, with clear menu options.
- **Progress Tracking**: Real-time in-place progress display showing current processing stage for each file.
- **AI-Powered Error Analysis**: Automatic error summarization using LLM to diagnose and explain processing failures.
- **Legacy File Migration**: Automatically migrates old unsanitized filenames to current format.
- **Comprehensive CLI Options**: Full command-line interface with configuration files, dependency checking, and validation modes.
- **Robust Error Handling**: Graceful fallbacks, detailed error logging, and pipeline continuation despite individual failures.

---

## Advanced Capabilities

### Unicode and Special Character Support

- Greek letters (σ, τ, α, β, γ, δ, ε, θ, λ, μ, π, ρ, φ, ψ, ω)
- Mathematical symbols and technical notation
- International characters and diacritics
- Automatic engine selection for optimal rendering

### Error Recovery & Analysis

- Multi-engine PDF generation with automatic fallbacks
- Detailed error reporting and debugging information
- Graceful degradation when PDF generation fails
- Pipeline continuation despite individual failures
- AI-powered error summarization for intelligent failure diagnosis
- Structured error logging with automatic summary generation

### Mixed Media Intelligence

- Smart file grouping and conflict resolution
- Priority-based processing (video > audio > text > images)
- Separate processing tracks for different media types
- Comprehensive coverage of all content in mixed folders

### Processing Efficiency

- Sequential processing eliminates race conditions and resource contention
- Bounded memory usage regardless of directory size
- Deterministic processing order for reproducible results
- Clean shutdown with proper resource cleanup on interrupt

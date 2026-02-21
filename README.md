# LangChain Video Transcription & Study Material Generator

## Overview

This project began as a simple experiment: transcribing and understanding a few educational videos.
It evolved into a **fully automated object-oriented pipeline** that transforms raw media content into **rich learning material** — complete with transcripts, structured summaries, glossaries, and practice questions — all orchestrated seamlessly.

The result is a system that demonstrates not only technical execution but also the **architectural thinking** required to design scalable, reliable, and extensible solutions for **mixed media processing** using modern software engineering principles.

---

## Getting Started

1. **Prerequisites**: Install Python, ffmpeg, Tesseract, Pandoc, LaTeX, and Ollama — [Prerequisites](docs/PREREQUISITES.md).
2. **Setup**: Clone the repo, create a virtual environment, and install dependencies — [Setup](docs/SETUP.md).
3. **Run**: `python main.py /path/to/media` — see [Running the Pipeline](docs/RUNNING_THE_PIPELINE.md) and [Usage](docs/USAGE.md) for CLI options.
4. **Advanced Usage**: `python main.py /path/to/media --llm-model llama3 --no-pdf --verbose` — see [Usage](docs/USAGE.md) for all CLI options.

---

## Key Features & CLI Options

### **Core Capabilities**

- **Multi-format Support**: Video (MP4, MKV, AVI, MOV), Audio (MP3, WAV, M4A, AAC), Text (.txt), Images (PNG, JPG, GIF, BMP, TIFF, WebP)
- **AI-Powered Processing**: Whisper transcription, LangChain content generation, Ollama LLM integration
- **PDF Generation**: Professional study materials with AI watermarking and attribution
- **Mixed Media Intelligence**: Process multiple media types in a single pipeline run

### **CLI Options**

```bash
# Basic usage
python main.py /path/to/media

# Advanced options
python main.py /path/to/media --llm-model llama3 --whisper-model large
python main.py /path/to/media --no-pdf --output-dir /custom/output
python main.py /path/to/media --verbose --no-spinner
python main.py /path/to/media --config config.json
python main.py /path/to/media --check-deps --validate-only
```

### **AI Content Marking**

- **Watermarking**: Automatic "AI Generated Content" watermarks on PDFs
- **Attribution**: Author information and contact details in PDF footers
- **Acknowledgments**: Detailed AI processing acknowledgment section
- **Customizable**: Configurable watermark text, opacity, and positioning

---

## Project Structure

```text
video_transcription/
├── main.py                    # Main entry point
├── src/
│   ├── cli/
│   │   └── main.py           # Command-line interface
│   ├── core/
│   │   ├── config.py        # Pipeline configuration
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── pipeline.py      # Main pipeline orchestration
│   ├── domain/
│   │   └── ai_marking.py    # AI content marking domain logic
│   ├── generators/
│   │   ├── enhanced_pdf_generator.py  # PDF generation with AI marking
│   │   ├── pdf_generator.py          # Basic PDF generation
│   │   └── study_generator.py        # Study material generation
│   ├── processors/           # Media processing components
│   └── utils/               # Utility functions
├── tests/
│   └── test_ai_marking.py   # Comprehensive test suite
├── docs/                    # Documentation
├── config/                  # Configuration files
└── requirements.txt         # Python dependencies
```

---

## Documentation

Detailed documentation is split into logical sections. Each link opens the corresponding document:

### **Architecture & Design**

- [**Architecture**](docs/ARCHITECTURE.md) — High-level design, components, design patterns, processing flow, file organization
- [**Processing Architecture**](docs/PROCESSING_ARCHITECTURE.md) — Three-pass processing, conflict resolution, PDF strategy
- [**Why Engineering Excellence**](docs/ENGINEERING_EXCELLENCE.md) — What makes this project stand out

### **Features & Capabilities**

- [**Features**](docs/FEATURES.md) — Capabilities and feature list
- [**AI Content Marking**](docs/AI_MARKING.md) — Watermarking, attribution, and acknowledgment for AI-generated PDFs
- [**Supported Media Types**](docs/SUPPORTED_MEDIA_TYPES.md) — Video, audio, text, and image formats
- [**Advanced Features**](docs/ADVANCED_FEATURES.md) — Unicode support, error recovery, mixed media intelligence
- [**Example CLI Output**](docs/EXAMPLE_CLI_OUTPUT.md) — Sample terminal output for mixed media

### **Reference**

- [**Tools & Technologies**](docs/TOOLS_AND_TECHNOLOGIES.md) — Stage-by-stage tools (ffmpeg, Whisper, Tesseract, LangChain, Pandoc, etc.)
- [**Customization**](docs/CUSTOMIZATION.md) — Study prompt and configuration
- [**Migration (v1 → v2)**](docs/MIGRATION.md) — Moving from script to OO version

### **Development & Testing**

- [**Testing**](tests/) — Comprehensive test suite for AI marking and PDF generation
- [**Configuration**](src/core/config.py) — Pipeline configuration and settings
- [**Exception Handling**](src/core/exceptions.py) — Custom error types and handling

### **Future Development**

- [**Next Changes**](docs/NEXT_CHANGES.md) — Planned SOA + DDD evolution (roadmap)

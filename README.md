# LangChain Video Transcription & Study Material Generator

## Overview

This project began as a simple experiment: transcribing and understanding a few educational videos.  
It evolved into a **fully automated object-oriented pipeline** that transforms raw media content into **rich learning material** — complete with transcripts, structured summaries, glossaries, and practice questions — all orchestrated seamlessly.

The result is a system that demonstrates not only technical execution but also the **architectural thinking** required to design scalable, reliable, and extensible solutions for **mixed media processing** using modern software engineering principles.

---

## Getting Started

1. **Prerequisites**: Install Python, ffmpeg, Tesseract, Pandoc, LaTeX, and Ollama — [Prerequisites](docs/PREREQUISITES.md).
2. **Setup**: Clone the repo, create a virtual environment, and install dependencies — [Setup](docs/SETUP.md).
3. **Run**: `python main.py ./data` — see [Running the Pipeline](docs/RUNNING_THE_PIPELINE.md) and [Usage](docs/USAGE.md) for CLI options.
4. **Usage**: `python main.py ./data` — see [Usage](docs/USAGE.md) for CLI options.

---

## Documentation

Detailed documentation is split into logical sections. Each link opens the corresponding document:

### **Architecture & Design**

- [**Architecture**](docs/ARCHITECTURE.md) — High-level design, components, design patterns, processing flow, file organization
- [**Processing Architecture**](docs/PROCESSING_ARCHITECTURE.md) — Three-pass processing, conflict resolution, PDF strategy
- [**Why Engineering Excellence**](docs/ENGINEERING_EXCELLENCE.md) — What makes this project stand out


### **Features & Capabilities**

- [**Features**](docs/FEATURES.md) — Capabilities and feature list
- [**Supported Media Types**](docs/SUPPORTED_MEDIA_TYPES.md) — Video, audio, text, and image formats
- [**Advanced Features**](docs/ADVANCED_FEATURES.md) — Unicode support, error recovery, mixed media intelligence
- [**Example CLI Output**](docs/EXAMPLE_CLI_OUTPUT.md) — Sample terminal output for mixed media

### **Reference**

- [**Tools & Technologies**](docs/TOOLS_AND_TECHNOLOGIES.md) — Stage-by-stage tools (ffmpeg, Whisper, Tesseract, LangChain, Pandoc, etc.)
- [**Customization**](docs/CUSTOMIZATION.md) — Study prompt and configuration
- [**Migration (v1 → v2)**](docs/MIGRATION.md) — Moving from script to OO version

### **Future Development**

- [**Next Changes**](docs/NEXT_CHANGES.md) — Planned SOA + DDD evolution (roadmap)

# LangChain Video Transcription & Study Material Generator

## Overview

This project began as a simple experiment: transcribing and understanding a few educational videos.  
It evolved into a **fully automated object-oriented pipeline** that transforms raw media content into **rich learning material** — complete with transcripts, structured summaries, glossaries, and practice questions — all orchestrated seamlessly.

The result is a system that demonstrates not only technical execution but also the **architectural thinking** required to design scalable, reliable, and extensible solutions for **mixed media processing** using modern software engineering principles.

---

## Architecture Highlights

### **Object-Oriented Design (v2.0)**

The project has been completely refactored into a modular, object-oriented architecture with:

- **Separation of Concerns**: Each component has a single, well-defined responsibility
- **Strategy Pattern**: Pluggable processors for different media types
- **Factory Pattern**: Dynamic processor creation based on file types
- **Observer Pattern**: Progress reporting and UI updates
- **Command Pattern**: Encapsulated processing operations

### **Core Components**

```text
src/
├── core/           # Pipeline orchestration, configuration, exceptions
├── processors/     # Media processors (audio, image, text, LLM)
├── generators/     # Output generators (PDF, study materials)
├── utils/          # File operations, UI, media utilities
└── cli/            # Command-line interface with signal handling
```

### **Design Benefits**

- **Maintainability**: Clean separation makes bugs easy to locate and fix
- **Extensibility**: Add new media types by implementing `BaseProcessor`
- **Testability**: Each component can be tested independently
- **Reusability**: Components can be used in other applications
- **Configuration-Driven**: Flexible behavior through configuration objects

---

## Features

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
- **Externalized Study Prompt**: Define the textbook author persona, structure, and rules in `study_prompt.txt` for easy customization.
- **Enhanced PDF Generation**: Multi-engine PDF generation with XeLaTeX (Unicode support) → pdfLaTeX (enhanced) → Minimal fallback.
- **Unicode Support**: Handles Greek letters, special characters, and international symbols in PDFs.
- **Smart File Naming**: Conflict-aware naming for mixed media (`{stem}_images.txt` for conflicts, `{stem}.txt` for clean cases).
- **CLI Experience**: Clean, readable progress updates with dynamic pipeline paths and spinners.
- **Robust Error Handling**: Graceful fallbacks and detailed error reporting for PDF generation issues.

---

## Tools & Technologies

| Stage                    | Tool/Technology                      | Purpose                              |
| ------------------------ | ------------------------------------ | ------------------------------------ |
| Video → Audio            | **ffmpeg**                           | Reliable audio extraction            |
| Audio → Text             | **Whisper**                          | State-of-the-art transcription       |
| Images → Text            | **Tesseract OCR**                    | Optical character recognition        |
| Text → Summary           | **LangChain Core** + **Ollama LLM**  | Prompt orchestration & summarization |
| Summary → Study Material | **LangChain PromptTemplate**         | Rich, structured learning content    |
| Study Prompt             | **study_prompt.txt**                 | Externalized customization of output |
| Markdown → PDF           | **Pandoc** + **XeLaTeX/pdfLaTeX**    | Professional document generation     |
| CLI UX                   | **Python sys.stdout + spinner**      | User-friendly progress visualization |

---

## Processing Architecture

The pipeline is designed as an **intelligent, modular sequence of transformations with a recursive traversal engine**. It automatically scans the entire directory subtree and processes all media types with a **three-pass approach**:

### **Three-Pass Processing System**

1. **Pass 1**: Video/Audio/Text groups (priority: video > audio > text)

2. **Pass 2**: Image groups (including those sharing stems with other media)

3. **Pass 3**: Loose images (folder-wide processing)

### **Smart Conflict Resolution**

- **Mixed stems**: `lecture1.mp4` + `lecture1.png` → `lecture1.txt` + `lecture1_images.txt`
- **Image-only stems**: `slides01.png` + `slides01.jpg` → `slides01.txt`
- **Loose images**: `random.gif` → `folder_images.txt`

### **PDF Generation Strategy**

- **XeLaTeX**: Native Unicode support for Greek letters and special characters
- **pdfLaTeX**: Enhanced with explicit Unicode character mappings
- **Minimal fallback**: Basic PDF generation without custom formatting

Each stage:
- Checks for existing artifacts (skip if already generated).
- Runs independently but feeds into the next stage.
- Updates CLI output in place, showing progress with spinners.
- Produces reusable artifacts (`.txt`, `.md`, `.pdf`) for downstream use.

This orchestration ensures **idempotency, scalability, and clarity** — critical traits for production-ready automation.

---

## Why This Project Showcases Engineering Excellence

- **Deep Research**: Started with exploring Whisper and LangChain, evolved into a full mixed-media pipeline.
- **Solution Design**: Identified pain points (manual transcription, scattered notes, mixed media chaos) and designed a structured workflow.
- **Architecture**: Modular, fault-tolerant, idempotent design with clear separation of concerns and intelligent conflict resolution.
- **Automation for Scale**: One command processes entire directories of mixed media, producing consistent, high-quality study material.
- **User Experience**: Thoughtful CLI design with progressive spinners, clean output, and robust error handling.
- **Compliance & Reliability**: Uses open-source, well-supported tools with reproducible environments (`requirements.txt`).
- **Unicode Excellence**: Comprehensive support for international characters and technical symbols in generated PDFs.

---

## Example CLI Output

_The script dynamically shows the pipeline based on mixed media content:_

```bash
AI is warming up... ready to crunch some knowledge.

# Mixed Media Folder
lecture1.mp4
    video > audio > transcript > study material > PDF

slides01.png + slides01.jpg
    images (2) > transcript > study material > PDF

lecture1.mp4 + lecture1.png
    video > audio > transcript > study material > PDF
    images (1) > transcript > study material > PDF

random.gif (loose image)
    images (1) > transcript > study material > PDF
```

---

## Supported Media Types

### **Video Files**

- `.mp4`, `.mkv`, `.avi`, `.mov`

### **Audio Files**

- `.mp3`, `.wav`, `.m4a`, `.aac`

### **Text Files**

- `.txt`

### **Image Files**

- `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.webp`

---

## Prerequisites

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

---

## Step-by-step setup

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

   - Install `ffmpeg`, `tesseract`, and `pandoc` + a LaTeX distribution using the commands in the **Prerequisites** section.

5. **Prepare Ollama**

   - Install Ollama and start the Ollama service.
   - Pull the model the script uses (default is `gemma3`):

   ```bash
     ollama pull gemma3
   ```

---

## How to run the pipeline

1. **Organize your content**
   - Create a folder such as `./data` and place your media inside it.
   - You can mix **any combination** of:
     - Video files (`.mp4`, `.mkv`, `.avi`, `.mov`)
     - Audio files (`.mp3`, `.wav`, `.m4a`, `.aac`)
     - Text transcripts (`.txt`)
     - Image files (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.webp`)
   - Subfolders are allowed; the script recursively walks the entire directory tree.
   - **Mixed folders are fully supported** - no need to separate media types.

2. **Run the script**

   ```bash
   # From the project root, with the virtualenv activated:
   python video_transcribe.py ./data
   ```

3. **Optional: skip PDF generation**

   ```bash
   python video_transcribe.py ./data --no-pdf
   ```

4. **Inspect outputs**

   - For each logical item, you will find:
     - A transcript: `<name>.txt` or `<name>_images.txt` for image groups
     - A study guide (Markdown): `<name>_study.md` or `<name>_images_study.md`
     - A PDF (if enabled and Pandoc/LaTeX are installed): `<name>.pdf` or `<name>_images.pdf`

5. **Re-running is safe**

   - The pipeline is **idempotent**: existing artifacts are reused, and only missing pieces are generated.
   - Mixed media processing is deterministic and conflict-free.

   ---

## Advanced Features

### **Unicode and Special Character Support**

- Greek letters (σ, τ, α, β, γ, δ, ε, θ, λ, μ, π, ρ, φ, ψ, ω)
- Mathematical symbols and technical notation
- International characters and diacritics
- Automatic engine selection for optimal rendering

### **Error Recovery**

- Multi-engine PDF generation with automatic fallbacks
- Detailed error reporting and debugging information
- Graceful degradation when PDF generation fails
- Pipeline continuation despite individual failures

### **Mixed Media Intelligence**

- Smart file grouping and conflict resolution
- Priority-based processing (video > audio > text > images)
- Separate processing tracks for different media types
- Comprehensive coverage of all content in mixed folders

---

## Customization

### **Study Prompt (`study_prompt.txt`)**

The AI's personality, output structure, and generation rules are defined in `config/study_prompt.txt`. You can modify this file to:
- Change the tone of the generated textbook chapter.
- Add or remove sections from the study material.
- Update the "Bloom's Taxonomy" based question requirements.
- Change the formatting or language requirements.

The script expects a `{transcript}` placeholder at the end of the file where the source text will be injected.

---

## Usage (v2.0 - Object-Oriented)

### **Basic Usage**

```bash
# Process with default settings
python main.py /path/to/media/folder

# Skip PDF generation
python main.py /path/to/media/folder --no-pdf

# Show detailed progress
python main.py /path/to/media/folder --verbose

# Use different models
python main.py /path/to/media/folder --whisper-model large --llm-model llama2
```

### **Advanced Options**

```bash
# Specify output directory
python main.py /path/to/media/folder --output-dir /output/path

# Check dependencies
python main.py /path/to/media/folder --check-deps

# Validate files without processing
python main.py /path/to/media/folder --validate-only

# Use configuration file
python main.py /path/to/media/folder --config config.json
```

### **Configuration File Support**

Create a JSON configuration file for complex setups:

```json
{
  "whisper_model": "large",
  "llm_model": "llama2",
  "generate_pdf": true,
  "verbose": true,
  "output_dir": "/custom/output"
}
```

---

## Migration from v1.0 (Script) to v2.0 (OO)

### **What Changed**

1. **Entry Point**: `python video_transcribe.py` → `python main.py`
2. **Configuration**: Command-line arguments now use modern CLI patterns
3. **Architecture**: Modular object-oriented design replaces monolithic script
4. **Error Handling**: Structured exception hierarchy with detailed error messages
5. **Testing**: Each component can be tested independently

### **Migration Steps**

1. **Update your workflow**:
   ```bash
   # Old
   python video_transcribe.py /path/to/media --no-pdf
   
   # New
   python main.py /path/to/media --no-pdf
   ```

2. **Configuration files**: Move any custom `study_prompt.txt` to `config/` directory

3. **Custom processors**: Extend `BaseProcessor` class instead of adding functions

### **Backward Compatibility**

The new OO implementation maintains full backward compatibility:
- Same input/output file formats
- Same processing logic and quality
- Same configuration options (with improved CLI)
- Same generated study material structure

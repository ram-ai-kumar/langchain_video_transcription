# LangChain Video Transcription & Study Material Generator

## Overview

This project began as a simple experiment: transcribing and understanding a few educational videos.  
It evolved into a **fully automated object-oriented pipeline** that transforms raw media content into **rich learning material** — complete with transcripts, structured summaries, glossaries, and practice questions — all orchestrated seamlessly.

The result is a system that demonstrates not only technical execution but also the **architectural thinking** required to design scalable, reliable, and extensible solutions for **mixed media processing** using modern software engineering principles.

---

## Architecture

### **High-Level Architecture Overview**

The system follows a **layered, object-oriented architecture** with clear separation of concerns. The architecture is designed for extensibility, maintainability, and reliability.

```text
┌─────────────────────────────────────────────────────────────┐
│                    CLI Layer (Entry Point)                  │
│  src/cli/main.py - VideoTranscriptionCLI                    │
│  - Argument parsing, signal handling, dependency checks     │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│              Core Pipeline Orchestrator                     │
│  src/core/pipeline.py - VideoTranscriptionPipeline         │
│  - Coordinates entire workflow                             │
│  - Manages three-pass processing system                    │
│  - Handles file grouping and conflict resolution           │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│ Processors   │ │ Generators   │ │   Utils    │
│              │ │              │ │            │
│ - Audio      │ │ - Study      │ │ - File     │
│ - Image      │ │ - PDF        │ │ - Media    │
│ - Text       │ │              │ │ - UI       │
│ - LLM        │ │              │ │            │
└──────────────┘ └──────────────┘ └────────────┘
```

### **Component Architecture**

#### **1. Entry Point Layer (`main.py`)**

The entry point is minimal and delegates to the CLI module:

- **Purpose**: Bootstrap the application and set up Python path
- **Responsibilities**:
  - Add `src` directory to Python path
  - Invoke CLI main function
- **Design**: Thin wrapper that enables clean module imports

#### **2. CLI Layer (`src/cli/main.py`)**

The command-line interface handles user interaction and application lifecycle:

- **Class**: `VideoTranscriptionCLI`
- **Responsibilities**:
  - **Argument Parsing**: Uses `argparse` for comprehensive CLI options
  - **Signal Handling**: Graceful shutdown on SIGINT/SIGTERM
  - **Configuration Management**: Creates `PipelineConfig` from CLI args and config files
  - **Dependency Validation**: Checks for required tools (Whisper, Tesseract, Pandoc, LaTeX)
  - **Error Handling**: User-friendly error messages and exit codes
- **Key Features**:
  - Supports JSON configuration files
  - Validates prerequisites before processing
  - Provides dependency checking mode (`--check-deps`)
  - Handles validation-only mode (`--validate-only`)

#### **3. Core Pipeline (`src/core/pipeline.py`)**

The heart of the system that orchestrates the entire processing workflow:

- **Class**: `VideoTranscriptionPipeline`
- **Responsibilities**:
  - **Directory Processing**: Recursively processes entire directory trees
  - **File Discovery**: Groups files by stem (filename without extension)
  - **Three-Pass Processing**: Implements intelligent processing order
  - **Conflict Resolution**: Handles mixed media with same stem names
  - **Progress Tracking**: Monitors and reports processing status
- **Processing Flow**:
  1. **Pass 1**: Process video/audio/text groups (priority: video > audio > text)
  2. **Pass 2**: Process image groups (including those sharing stems with other media)
  3. **Pass 3**: Process loose images (folder-wide processing)
- **Key Methods**:
  - `process_directory()`: Main entry point for directory processing
  - `process_single_source()`: Processes individual media files through the pipeline
  - `_process_media_groups()`: Handles Pass 1 processing
  - `_process_image_groups()`: Handles Pass 2 processing
  - `_process_loose_images()`: Handles Pass 3 processing
- **Idempotency**: Checks for existing artifacts and skips regeneration

#### **4. Processors (`src/processors/`)**

Processors implement the **Strategy Pattern** for handling different media types:

**Base Processor (`base.py`)**:

- **Abstract Class**: `BaseProcessor`
- **Purpose**: Defines common interface for all processors
- **Key Methods**:
  - `can_process()`: Type checking
  - `process()`: Main processing logic (abstract)
  - `validate_input()`: Input validation
  - `ensure_output_dir()`: Directory creation
  - `get_output_path()`: Path generation

**Audio Processor (`audio_processor.py`)**:

- **Class**: `AudioProcessor`
- **Capabilities**:
  - Extracts audio from video using `ffmpeg` subprocess
  - Transcribes audio using OpenAI Whisper
  - Lazy model loading (loads only when needed)
- **Methods**:
  - `process()`: Transcribes audio to text
  - `extract_audio_from_video()`: Extracts audio stream from video
- **Dependencies**: `whisper`, `ffmpeg`

**Image Processor (`image_processor.py`)**:

- **Class**: `ImageProcessor`
- **Capabilities**:
  - OCR text extraction using Tesseract
  - Batch processing of multiple images
  - Combines text from multiple images
- **Methods**:
  - `process()`: Processes multiple images to single transcript
  - `process_single_image()`: Processes single image
- **Dependencies**: `pytesseract`, `PIL/Pillow`

**Text Processor (`text_processor.py`)**:

- **Class**: `TextProcessor`
- **Capabilities**:
  - Validates text files
  - Copies text files to output location
  - Provides text statistics
- **Methods**:
  - `process()`: Validates and processes text file
  - `validate_text_content()`: Checks for readable content
  - `get_text_stats()`: Returns file statistics

**LLM Processor (`llm_processor.py`)**:

- **Class**: `LLMProcessor`
- **Capabilities**:
  - Generates study materials using LangChain + Ollama
  - Loads prompt templates from external files
  - Validates LLM connectivity
- **Methods**:
  - `process()`: Generates study material from transcript
  - `validate_llm_connection()`: Tests LLM availability
  - `get_model_info()`: Returns model configuration
- **Dependencies**: `langchain-core`, `langchain-ollama`
- **Architecture**: Uses LangChain's `RunnableSequence` to chain prompt template with LLM

#### **5. Generators (`src/generators/`)**

Generators handle output file creation:

**Study Material Generator (`study_generator.py`)**:

- **Class**: `StudyMaterialGenerator`
- **Responsibilities**:
  - Coordinates LLM processing and PDF generation
  - Manages output file paths
  - Validates prerequisites
  - Handles errors gracefully (PDF failures don't stop study material generation)
- **Methods**:
  - `generate()`: Main generation method
  - `validate_prerequisites()`: Checks LLM and PDF dependencies
  - `get_generator_info()`: Returns configuration information

**PDF Generator (`pdf_generator.py`)**:

- **Class**: `PDFGenerator`
- **Capabilities**:
  - Multi-engine PDF generation with fallback strategy
  - Unicode support for special characters
  - Custom LaTeX header integration
- **PDF Engines** (in order of preference):
  1. **XeLaTeX**: Native Unicode support
  2. **pdfLaTeX**: Enhanced with Unicode mappings
  3. **Minimal Fallback**: Basic PDF without custom formatting
- **Methods**:
  - `generate_pdf()`: Main PDF generation with fallback logic
  - `_generate_with_engine()`: Generates PDF with specific engine
  - `_generate_minimal_fallback()`: Basic PDF generation
  - `validate_dependencies()`: Checks Pandoc and LaTeX availability
- **Dependencies**: `pandoc`, LaTeX distribution (XeLaTeX or pdfLaTeX)

#### **6. Utilities (`src/utils/`)**

Supporting utilities for file operations, media handling, and UI:

**File Discovery (`file_utils.py`)**:

- **Class**: `FileDiscovery`
- **Capabilities**:
  - Recursive file discovery in directory trees
  - Groups files by stem (deterministic ordering)
  - Determines primary source (video > audio > text > images)
  - Generates output paths
- **Key Methods**:
  - `discover_files()`: Finds all supported files recursively
  - `group_files_by_stem()`: Groups files by filename stem
  - `find_primary_source()`: Determines processing priority
  - `get_output_paths()`: Generates standard output paths

**File Manager (`file_utils.py`)**:

- **Class**: `FileManager` (static methods)
- **Capabilities**:
  - Safe file operations with encoding fallbacks
  - Directory creation
  - File validation and statistics
- **Methods**:
  - `safe_read_text()`: Reads text with encoding fallbacks
  - `safe_write_text()`: Writes text safely
  - `ensure_directory()`: Creates directories
  - `get_file_size()`: Returns file size
  - `is_file_empty()`: Checks for empty files

**Media Utilities (`media_utils.py`)**:

- **Classes**:
  - `MediaTypeDetector`: Categorizes files by media type
  - `MediaProcessorFactory`: Factory for creating processors (Factory Pattern)
  - `MediaFileValidator`: Validates media files
  - `ProcessingPathGenerator`: Generates processing paths
- **Purpose**: Provides media type detection and processor creation

**UI Utilities (`ui_utils.py`)**:

- **Classes**:
  - `ColorFormatter`: Terminal color formatting
  - `StatusReporter`: Status message reporting
  - `ProgressReporter`: Progress tracking
  - `Spinner`: Animated progress spinner
- **Purpose**: User-friendly CLI output and progress indication

#### **7. Configuration (`src/core/config.py`)**

Centralized configuration management:

- **Class**: `PipelineConfig` (dataclass)
- **Configuration Categories**:
  - **Model Settings**: Whisper model, LLM model
  - **Output Settings**: PDF generation flag, output directory
  - **File Extensions**: Supported video, audio, text, image formats
  - **Processing Settings**: FFmpeg quality, OCR language, transcription language
  - **UI Settings**: Spinner display, verbose mode
  - **Paths**: Prompt file, LaTeX header file
- **Features**:
  - Default values for all settings
  - Automatic path resolution
  - File existence validation
  - Type checking via dataclass

#### **8. Exception Handling (`src/core/exceptions.py`)**

Hierarchical exception structure for precise error handling:

```python
VideoTranscriptionError (base)
├── ProcessingError
│   ├── OCRProcessingError
│   ├── TranscriptionError
│   └── LLMProcessingError
├── ConfigurationError
├── ModelLoadError
└── PDFGenerationError
```

- **Purpose**: Provides context-aware error messages
- **Benefits**: Enables precise error handling and user-friendly error reporting

### **Design Patterns**

The architecture employs several design patterns:

1. **Strategy Pattern**:
   - Processors implement `BaseProcessor` interface
   - Runtime selection of processing strategy based on media type
   - Example: `AudioProcessor`, `ImageProcessor`, `TextProcessor` are interchangeable strategies

2. **Factory Pattern**:
   - `MediaProcessorFactory` creates appropriate processors
   - Encapsulates processor creation logic
   - Enables lazy initialization

3. **Template Method Pattern**:
   - `BaseProcessor` defines processing template
   - Subclasses implement specific steps
   - Common validation and path handling in base class

4. **Observer Pattern**:
   - Progress reporting and UI updates
   - `StatusReporter` and `ProgressReporter` observe processing events
   - Decouples processing logic from UI updates

5. **Command Pattern**:
   - Processing operations encapsulated as methods
   - Enables undo/redo potential (future enhancement)
   - Supports idempotent operations

### **Processing Flow**

The complete processing flow from input to output:

```text
Input Media Files (Video/Audio/Text/Images)
    ↓
File Discovery & Grouping
    ├─ Recursive directory traversal
    ├─ Group files by stem (filename without extension)
    └─ Determine primary source (video > audio > text > images)
    ↓
Three-Pass Processing System:
    ├─ Pass 1: Video/Audio/Text Groups
    │   ├─ Extract audio from video (if needed)
    │   ├─ Transcribe audio to text (if needed)
    │   └─ Generate study material from transcript
    │
    ├─ Pass 2: Image Groups
    │   ├─ OCR images to text
    │   └─ Generate study material from transcript
    │
    └─ Pass 3: Loose Images
        ├─ OCR images to text
        └─ Generate study material from transcript
    ↓
Study Material Generation
    ├─ Load prompt template from config/study_prompt.txt
    ├─ Invoke LLM with transcript
    └─ Write study material markdown
    ↓
PDF Generation (optional)
    ├─ Try XeLaTeX (Unicode support)
    ├─ Fallback to pdfLaTeX (enhanced)
    └─ Fallback to minimal PDF (basic)
    ↓
Output Files
    ├─ Transcript: {name}.txt or {name}_images.txt
    ├─ Study Material: {name}_study.md
    └─ PDF: {name}.pdf (if enabled)
```

### **Key Architectural Features**

1. **Separation of Concerns**:
   - Each component has a single, well-defined responsibility
   - Changes to one component don't affect others
   - Clear boundaries between layers

2. **Extensibility**:
   - Add new media types by implementing `BaseProcessor`
   - Add new output formats by extending generators
   - Configuration-driven behavior

3. **Testability**:
   - Components can be tested independently
   - Dependency injection via configuration
   - Mockable interfaces

4. **Idempotency**:
   - Safe to re-run on same directory
   - Checks for existing artifacts
   - Skips regeneration of existing files

5. **Error Resilience**:
   - Graceful degradation (PDF failures don't stop processing)
   - Detailed error messages with context
   - Hierarchical exception handling

6. **Deterministic Processing**:
   - Consistent file ordering (lexicographic)
   - Repeatable results
   - Predictable output naming

7. **Unicode Support**:
   - Handles special characters in PDFs
   - Multiple LaTeX engine fallbacks
   - Encoding-aware file operations

### **File Organization**

```text
src/
├── core/                    # Core orchestration and configuration
│   ├── pipeline.py          # Main pipeline orchestrator
│   ├── config.py            # Configuration management
│   └── exceptions.py        # Exception hierarchy
│
├── processors/              # Media processors (Strategy Pattern)
│   ├── base.py              # Abstract base processor
│   ├── audio_processor.py   # Audio transcription
│   ├── image_processor.py   # Image OCR
│   ├── text_processor.py    # Text validation
│   └── llm_processor.py     # LLM-based generation
│
├── generators/              # Output generators
│   ├── study_generator.py   # Study material coordination
│   └── pdf_generator.py     # PDF generation
│
├── utils/                   # Supporting utilities
│   ├── file_utils.py        # File operations and discovery
│   ├── media_utils.py       # Media type detection and factory
│   └── ui_utils.py          # CLI UI and progress reporting
│
└── cli/                     # Command-line interface
    └── main.py              # CLI implementation
```

### **Extension Points**

The architecture provides several extension points:

1. **New Media Types**: Implement `BaseProcessor` and add to factory
2. **New Output Formats**: Extend generators or create new generator classes
3. **Custom Processing**: Override pipeline methods for custom workflows
4. **Configuration**: Extend `PipelineConfig` for new settings
5. **Error Handling**: Add custom exceptions to the hierarchy

### **Design Benefits**

- **Maintainability**: Clean separation makes bugs easy to locate and fix
- **Extensibility**: Add new media types by implementing `BaseProcessor`
- **Testability**: Each component can be tested independently
- **Reusability**: Components can be used in other applications
- **Configuration-Driven**: Flexible behavior through configuration objects
- **Production-Ready**: Error handling, logging, and graceful degradation

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
- **Externalized Study Prompt**: Define the textbook author persona, structure, and rules in `config/study_prompt.txt` for easy customization.
- **Enhanced PDF Generation**: Multi-engine PDF generation with XeLaTeX (Unicode support) → pdfLaTeX (enhanced) → Minimal fallback.
- **Unicode Support**: Handles Greek letters, special characters, and international symbols in PDFs.
- **Smart File Naming**: Conflict-aware naming for mixed media (`{stem}_images.txt` for conflicts, `{stem}.txt` for clean cases).
- **CLI Experience**: Clean, readable progress updates with dynamic pipeline paths and spinners.
- **Robust Error Handling**: Graceful fallbacks and detailed error reporting for PDF generation issues.

---

## Tools & Technologies

| Stage                    | Tool/Technology                     | Purpose                              |
| ------------------------ | ----------------------------------- | ------------------------------------ |
| Video → Audio            | **ffmpeg**                          | Reliable audio extraction            |
| Audio → Text             | **Whisper**                         | State-of-the-art transcription       |
| Images → Text            | **Tesseract OCR**                   | Optical character recognition        |
| Text → Summary           | **LangChain Core** + **Ollama LLM** | Prompt orchestration & summarization |
| Summary → Study Material | **LangChain PromptTemplate**        | Rich, structured learning content    |
| Study Prompt             | **config/study_prompt.txt**         | Externalized customization of output |
| Markdown → PDF           | **Pandoc** + **XeLaTeX/pdfLaTeX**   | Professional document generation     |
| CLI UX                   | **Python sys.stdout + spinner**     | User-friendly progress visualization |

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
   python main.py ./data
   ```

3. **Optional: skip PDF generation**

   ```bash
   python main.py ./data --no-pdf
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

The Object Oriented implementation maintains full backward compatibility:

- Same input/output file formats
- Same processing logic and quality
- Same configuration options (with improved CLI)
- Same generated study material structure

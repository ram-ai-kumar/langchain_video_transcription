# Architecture

[← Back to README](../README.md)

## High-Level Architecture Overview

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
│  src/core/pipeline.py - VideoTranscriptionPipeline          │
│  - Coordinates entire workflow                              │
│  - Manages three-pass processing system                     │
│  - Handles file grouping and conflict resolution            │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│ Processors   │ │ Generators  │ │   Utils    │
│              │ │             │ │            │
│ - Audio      │ │ - Study     │ │ - File     │
│ - Image      │ │ - PDF       │ │ - Media    │
│ - Text       │ │             │ │ - UI       │
│ - LLM        │ │             │ │            │
└──────────────┘ └─────────────┘ └────────────┘
```

## Component Architecture

### 1. Entry Point Layer (`main.py`)

The entry point is minimal and delegates to the CLI module:

- **Purpose**: Bootstrap the application and set up Python path
- **Responsibilities**:
  - Add `src` directory to Python path
  - Invoke CLI main function
- **Design**: Thin wrapper that enables clean module imports

### 2. CLI Layer (`src/cli/main.py`)

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

### 3. Core Pipeline (`src/core/pipeline.py`)

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

### 4. Processors (`src/processors/`)

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

### 5. Generators (`src/generators/`)

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

### 6. Utilities (`src/utils/`)

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

### 7. Configuration (`src/core/config.py`)

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

### 8. Exception Handling (`src/core/exceptions.py`)

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

## Design Patterns

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

## Processing Flow

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

## Key Architectural Features

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

## File Organization

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
│   ├── text_processor.py   # Text validation
│   └── llm_processor.py     # LLM-based generation
│
├── generators/              # Output generators
│   ├── study_generator.py   # Study material coordination
│   └── pdf_generator.py    # PDF generation
│
├── utils/                   # Supporting utilities
│   ├── file_utils.py        # File operations and discovery
│   ├── media_utils.py       # Media type detection and factory
│   └── ui_utils.py          # CLI UI and progress reporting
│
└── cli/                     # Command-line interface
    └── main.py              # CLI implementation
```

## Extension Points

The architecture provides several extension points:

1. **New Media Types**: Implement `BaseProcessor` and add to factory
2. **New Output Formats**: Extend generators or create new generator classes
3. **Custom Processing**: Override pipeline methods for custom workflows
4. **Configuration**: Extend `PipelineConfig` for new settings
5. **Error Handling**: Add custom exceptions to the hierarchy

## Design Benefits

- **Maintainability**: Clean separation makes bugs easy to locate and fix
- **Extensibility**: Add new media types by implementing `BaseProcessor`
- **Testability**: Each component can be tested independently
- **Reusability**: Components can be used in other applications
- **Configuration-Driven**: Flexible behavior through configuration objects
- **Production-Ready**: Error handling, logging, and graceful degradation

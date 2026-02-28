# Next Changes: Upcoming Architecture Evolution

[← Back to README](../README.md)

This document describes **planned improvements and architecture evolution** for the Video Transcription & Study Material Generator. Items are ordered from most critical to least significant, followed by long-term architectural proposals: **Service-Oriented Architecture (SOA)** and **Domain-Driven Design (DDD)**.

---

## **Critical Improvements (Immediate Priority)**

### **1. Replace `print()` with the `logging` Module**

**Current State**: Every processor and utility uses bare `print()` statements throughout the codebase

**Required Actions**:

- Adopt `logging.getLogger(__name__)` in every module
- Wire `--verbose` CLI flag to log levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- Add a single root logger configuration in `src/core/pipeline.py` at startup
- Remove all bare `print()` calls from processors, generators, and utilities

**Example**:

```python
# Before
print(f"Processing {audio_path}...")

# After
import logging
logger = logging.getLogger(__name__)
logger.info("Processing %s", audio_path)
```

**Impact**: Makes output filterable and redirectable; critical for debugging batch runs and production deployments

---

### **2. Testing Infrastructure & CI/CD**

**Current State**: Minimal testing — only `test_ai_marking.py` exists; no CI/CD pipeline

**Required Actions**:

- **Add test dependencies**:
  ```text
  pytest>=7.0.0
  pytest-cov>=4.0.0
  pytest-mock>=3.10.0
  ```
- **Create comprehensive test suite** covering:
  - Unit tests for all processors (`AudioProcessor`, `ImageProcessor`, `TextProcessor`, `LLMProcessor`)
  - Integration tests for pipeline workflows
  - CLI argument parsing tests
  - Configuration validation tests
  - File utility and media detection tests
- **Implement test fixtures** for temporary files and mock models
- **Add GitHub Actions CI/CD** (`.github/workflows/ci.yml`):
  - Run `pytest` on every push and pull request
  - Run `ruff` or `flake8` linting
  - Run `mypy` type checking
  - Enforce minimum 60% code coverage

**Impact**: Essential for code reliability and enabling safe refactoring

---

### **3. Async / Parallel File Processing**

**Current State**: Sequential processing — 10 independent lecture videos block each other

**Required Actions**:

- Use `concurrent.futures.ThreadPoolExecutor` for I/O-bound transcription and LLM calls
- Expose `max_workers` as a CLI option and config field
- Add progress tracking that works across concurrent jobs

**Example**:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_directory_concurrent(self, directory: Path) -> list[ProcessResult]:
    with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
        futures = {
            executor.submit(self.process_single_source, file, media_type): file
            for file, media_type in files_to_process
        }
        results = []
        for future in as_completed(futures):
            results.append(future.result())
    return results
```

**Impact**: Significant performance improvement for batch processing

---

### **4. Populate the `src/domain/` Layer**

**Current State**: `src/domain/` only contains `__init__.py`; business logic is scattered across processors and the pipeline

**Required Actions**:

- Create `TranscriptDocument` value object
- Create `StudyMaterial` aggregate
- Move `AIMarkingConfig` / `WatermarkConfig` from `pdf_generator.py` into domain
- Extract file-grouping and conflict-resolution business rules from `pipeline.py` into domain services
- Ensure the domain layer has zero infrastructure dependencies

**Impact**: Makes business rules testable in isolation; enables the SOA/DDD evolution described later

---

### **5. Configuration Validation with Pydantic**

**Current State**: `PipelineConfig` is a plain `@dataclass` — invalid values (e.g., `whisper_model="huge"`) fail late in the pipeline with cryptic errors

**Required Actions**:

- Migrate `PipelineConfig` to `pydantic.BaseModel`
- Add field-level validators:
  ```python
  from pydantic import BaseModel, field_validator

  class PipelineConfig(BaseModel):
      whisper_model: str = "medium"
      llm_model: str = "gemma3"

      @field_validator("whisper_model")
      @classmethod
      def validate_whisper_model(cls, v: str) -> str:
          valid = {"tiny", "base", "small", "medium", "large", "large-v2", "large-v3"}
          if v not in valid:
              raise ValueError(f"Invalid whisper model '{v}'. Choose from: {sorted(valid)}")
          return v
  ```
- Add environment variable support for sensitive settings
- Support YAML/TOML config files alongside JSON

**Impact**: Catches bad inputs at startup with clear error messages instead of mid-pipeline crashes

---

## **Medium-Term Enhancements**

### **6. Temporary File Cleanup**

**Current State**: Audio extracted from video (`.wav`/`.mp3` temp files) is not guaranteed to be cleaned up when processing fails mid-run

**Required Actions**:

- Wrap audio extraction in a context manager or `try/finally` block:
  ```python
  import tempfile

  with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
      extract_audio(video_path, tmp.name)
      transcribe(tmp.name)
  ```
- Audit all temporary file creation paths and ensure cleanup in failure scenarios

**Impact**: Prevents disk space accumulation from repeated failed runs

---

### **7. LLM Connection Reuse + Retry**

**Current State**: A new `OllamaLLM` instance is created per file; `tenacity` is already in `requirements.txt` but unused

**Required Actions**:

- Instantiate `OllamaLLM` once at pipeline startup and pass it through to all processors
- Add retry with exponential backoff for LLM calls:
  ```python
  from tenacity import retry, stop_after_attempt, wait_exponential

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
  def generate_study_material(self, content: str) -> str:
      return self.chain.invoke({"content": content})
  ```
- Add a circuit breaker to stop retrying if Ollama is clearly unavailable

**Impact**: Reduces connection overhead for batch runs; prevents transient LLM failures from aborting the pipeline

---

### **8. Error Handling & Resilience**

**Current State**: Basic exception handling with custom types; transient failures abort processing

**Required Actions**:

- Improve error context — include file paths and pipeline stage in all exception messages
- Add graceful degradation: if PDF generation fails, still save the markdown output
- Log failures per-file and continue processing remaining files instead of stopping

**Impact**: Prevents one bad file from aborting a long batch run

---

### **9. Security & Input Validation**

**Current State**: Basic file existence checks only

**Required Actions**:

- Sanitize file paths to prevent directory traversal attacks
- Validate file sizes before loading into memory to prevent resource exhaustion
- Add file type verification beyond extension checking (magic number / MIME sniffing)
- Implement dependency injection for processors to improve testability and reduce hidden coupling

**Impact**: Prevents security vulnerabilities and resource abuse

---

### **10. Code Quality & Developer Experience**

**Current State**: Good structure but missing tooling; type hints exist but are not enforced

**Required Actions**:

- Add `pyproject.toml` to consolidate version, tool configuration, and metadata:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]

  [tool.mypy]
  strict = true

  [tool.ruff]
  line-length = 100
  ```
- Add pre-commit hooks: `ruff`, `mypy`, `pytest`
- Add code coverage reporting with minimum thresholds
- Create contributor development guide

**Impact**: Improved code maintainability and developer onboarding

---

## **Nice-to-Have / Polish**

### **11. OCR Quality Improvement**

**Current State**: Raw `pytesseract.image_to_string()` with default config gives poor results on lecture slides with dark backgrounds or small fonts

**Required Actions**:

- Pre-process images before OCR: convert to grayscale, apply adaptive thresholding
- Pass `--psm 6` (assume uniform block of text) to Tesseract for slide-like images
- Use `config.ocr_language` consistently — the current code falls back to a hard-coded `"eng"` in places

**Impact**: Meaningfully better text extraction from lecture slide images

---

### **12. Whisper Model Caching Across Runs**

**Current State**: The Whisper model is loaded once per pipeline invocation but reloaded on every new run, which is slow

**Required Actions**:

- Document model caching behavior clearly
- Consider a persistent model server pattern (similar to Ollama) for high-frequency use cases
- At minimum, detect if the model is already cached locally and log the load time

**Impact**: Reduces startup time for repeated processing sessions

---

### **13. Study Prompt Versioning**

**Current State**: `config/study_prompt.txt` is a flat text file with no version metadata; impossible to tell which prompt version produced which study material

**Required Actions**:

- Embed a `PROMPT_VERSION` header comment in the file (e.g., `# version: 1.2`)
- Stamp the prompt version into the generated study material metadata or footer
- Keep a short changelog at the top of the prompt file

**Impact**: Reproducibility — enables comparing output quality across prompt versions

---

### **14. Dependency Management with `pip-compile`**

**Current State**: `requirements.txt` lists 54 packages, many of which are transitive dependencies mixed with direct ones

**Required Actions**:

- Split into `requirements.in` (direct dependencies only) and generate `requirements.txt` via `pip-compile`
- Move version, project metadata, and tool config into `pyproject.toml`

**Impact**: Cleaner dependency management; easier to upgrade packages safely

---

### **15. Clarify or Populate `src/domain/` Naming**

**Current State**: The directory is labeled `domain/` (DDD language) but `src/core/pipeline.py` is doing the actual domain orchestration; `src/domain/` is empty

**Required Actions**:

- Either commit to DDD properly (populate with aggregates, entities, value objects — see DDD section below)
- Or rename to `src/models/` to avoid misleading contributors about architectural intent

**Impact**: Reduces confusion for contributors about where business logic belongs

---

### **16. Enhanced CLI Features**

**Current State**: Comprehensive but some user experience gaps

**Required Actions**:

- Add dry-run mode (`--dry-run`) for previewing operations without processing
- Add interactive configuration wizard for first-time users
- Improve progress bars with ETA estimates for long transcription jobs

**Impact**: Better user experience and reduced configuration errors

---

### **17. Plugin Architecture**

**Proposed Enhancement**: Allow custom processors and generators via a plugin system

```python
class PluginManager:
    def load_plugins(self, plugin_dir: Path):
        for plugin_file in plugin_dir.glob("*.py"):
            self.load_plugin(plugin_file)

    def register_processor(self, processor_class: type[BaseProcessor]):
        self._processors.append(processor_class)
```

**Use Cases**: Custom media formats, specialized processing pipelines, organization-specific output formats

---

### **18. REST API Interface**

**Proposed Enhancement**: Web interface for remote processing

```python
from fastapi import FastAPI, UploadFile

app = FastAPI()

@app.post("/process")
async def process_files(files: list[UploadFile]):
    job_id = await create_processing_job(files)
    return {"job_id": job_id, "status": "queued"}

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    return await get_job_progress(job_id)
```

**Use Cases**: Web interface, integration with LMS platforms, multi-user environments

---

### **19. Database Integration**

**Proposed Enhancement**: Metadata storage and search capabilities

**Features**:

- Metadata storage for processed files (timestamps, processing stats)
- Job queue system for background processing
- Search capabilities across generated content
- Processing history and analytics

**Use Cases**: Large-scale deployments, content management systems

---

### **20. Advanced PDF Features**

**Proposed Enhancement**: Enhanced PDF generation with more customization

**Features**:

- Custom themes and styling options
- Interactive elements (bookmarks, internal hyperlinks)
- Batch PDF generation with a master table of contents
- PDF optimization for different use cases (print vs. screen)

---

## **Architecture Evolution: Service-Oriented Architecture (SOA)**

### **Current Architecture Limitations**

While the current architecture is well-structured, it has some limitations:

1. **Tight Coupling**: Processors directly depend on infrastructure (Whisper, Tesseract, Pandoc)
2. **Limited Scalability**: Monolithic design makes independent scaling difficult
3. **Infrastructure Leakage**: File paths, external tool calls, and technical details are mixed with business logic
4. **Limited Testability**: Hard to mock external dependencies and test business rules in isolation
5. **No Clear Service Boundaries**: Functionality is grouped by technical concerns rather than business capabilities

### **Proposed SOA Structure**

```text
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  CLI, REST API, Web UI, etc.                                │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    Application Services                       │
│  - TranscriptionOrchestrationService                        │
│  - StudyMaterialGenerationService                           │
│  - MediaProcessingService                                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│ Domain       │ │Infrastructure│ │ External   │
│ Services     │ │ Services     │ │ Services   │
│              │ │              │ │            │
│ - Audio      │ │ - File       │ │ - Whisper  │
│   Transcript │ │   Storage    │ │ - Tesseract│
│ - OCR        │ │ - PDF        │ │ - Ollama   │
│ - LLM        │ │   Generation │ │            │
│   Generation │ │              │ │            │
└──────────────┘ └──────────────┘ └────────────┘
```

### **Key Services**

**Application Services** (Orchestration Layer):

- **`TranscriptionOrchestrationService`**: Coordinates the entire transcription workflow, manages three-pass processing, handles file grouping and conflict resolution
- **`StudyMaterialGenerationService`**: Orchestrates study material creation, coordinates LLM processing and PDF generation
- **`MediaProcessingService`**: Handles media type detection, routes to appropriate domain services, manages processing priority

**Domain Services** (Business Logic Layer):

- **`AudioTranscriptionService`**: `transcribe_audio(audio_file: AudioFile) -> Transcript`
- **`OCRService`**: `extract_text(images: list[ImageFile]) -> Transcript`
- **`LLMGenerationService`**: `generate_study_material(transcript: Transcript) -> StudyMaterial`

**Infrastructure Services** (Technical Layer):

- **`FileStorageService`**: `save_file(content: bytes, path: Path)`, `read_file(path: Path) -> bytes`
- **`PDFGenerationService`**: `generate_pdf(markdown: str, output_path: Path) -> PDF`

**External Services** (Integration Layer):

- **`WhisperService`**: Wraps Whisper model calls
- **`TesseractService`**: Wraps Tesseract OCR calls
- **`OllamaService`**: Wraps Ollama LLM API calls

### **Benefits of SOA**

1. **Loose Coupling**: Services communicate through well-defined interfaces
2. **Reusability**: Services can be reused across different applications
3. **Testability**: Easy to mock service interfaces for unit testing
4. **Scalability**: Services can be scaled independently
5. **Maintainability**: Changes to one service don't affect others
6. **Technology Independence**: Can swap implementations without changing interfaces

---

## **Architecture Evolution: Domain-Driven Design (DDD)**

DDD focuses on **modeling the business domain** using domain concepts, entities, value objects, and aggregates.

### **Domain Model Structure**

```text
Domain Layer
├── Entities (Identity-based)
│   ├── MediaFile
│   ├── Transcript
│   ├── StudyMaterial
│   └── ProcessingJob
│
├── Value Objects (Immutable, equality by value)
│   ├── FilePath
│   ├── MediaType
│   ├── ProcessingStatus
│   ├── TranscriptContent
│   └── StudyMaterialContent
│
├── Aggregates (Consistency boundaries)
│   ├── MediaProcessingAggregate
│   └── StudyMaterialAggregate
│
├── Domain Services (Stateless operations)
│   ├── ConflictResolver
│   ├── FileGroupingStrategy
│   └── ProcessingPriorityCalculator
│
└── Repositories (Abstraction for persistence)
    ├── MediaFileRepository
    ├── TranscriptRepository
    └── StudyMaterialRepository
```

### **Domain Entities**

**`MediaFile`** (Entity):

```python
class MediaFile:
    """Domain entity representing a media file."""

    def __init__(self, file_id: str, path: FilePath, media_type: MediaType):
        self.file_id = file_id
        self.path = path
        self.media_type = media_type
        self.metadata: dict[str, Any] = {}

    def can_be_transcribed(self) -> bool:
        """Business rule: Can this file be transcribed?"""
        return self.media_type in [MediaType.AUDIO, MediaType.VIDEO]

    def get_processing_priority(self) -> int:
        """Business rule: Priority for processing (video > audio > text > image)."""
        priority_map = {
            MediaType.VIDEO: 1,
            MediaType.AUDIO: 2,
            MediaType.TEXT: 3,
            MediaType.IMAGE: 4,
        }
        return priority_map.get(self.media_type, 999)
```

**`Transcript`** (Entity):

```python
class Transcript:
    """Domain entity representing a transcript."""

    def __init__(self, transcript_id: str, content: TranscriptContent, source: MediaFile):
        self.transcript_id = transcript_id
        self.content = content
        self.source = source
        self.created_at: datetime = datetime.now()
        self.status: ProcessingStatus = ProcessingStatus.CREATED

    def is_empty(self) -> bool:
        return self.content.is_empty()

    def can_generate_study_material(self) -> bool:
        return not self.is_empty() and self.status == ProcessingStatus.COMPLETED
```

**`StudyMaterial`** (Entity):

```python
class StudyMaterial:
    """Domain entity representing generated study material."""

    def __init__(self, material_id: str, content: StudyMaterialContent, transcript: Transcript):
        self.material_id = material_id
        self.content = content
        self.transcript = transcript
        self.pdf_path: FilePath | None = None
        self.created_at: datetime = datetime.now()
```

### **Value Objects**

**`MediaType`** (Value Object):

```python
@dataclass(frozen=True)
class MediaType:
    """Immutable value object representing media type."""

    name: str
    extensions: tuple[str, ...]

    VIDEO = MediaType("video", (".mp4", ".mkv", ".avi", ".mov"))
    AUDIO = MediaType("audio", (".mp3", ".wav", ".m4a", ".aac"))
    TEXT = MediaType("text", (".txt",))
    IMAGE = MediaType("image", (".png", ".jpg", ".jpeg", ".gif"))

    @classmethod
    def from_extension(cls, ext: str) -> "MediaType | None":
        ext_lower = ext.lower()
        for media_type in [cls.VIDEO, cls.AUDIO, cls.TEXT, cls.IMAGE]:
            if ext_lower in media_type.extensions:
                return media_type
        return None
```

**`ProcessingStatus`** (Value Object):

```python
@dataclass(frozen=True)
class ProcessingStatus:
    value: str

    PENDING = ProcessingStatus("pending")
    IN_PROGRESS = ProcessingStatus("in_progress")
    COMPLETED = ProcessingStatus("completed")
    FAILED = ProcessingStatus("failed")
    SKIPPED = ProcessingStatus("skipped")
```

### **Domain Services**

**`ConflictResolver`** (Domain Service):

```python
class ConflictResolver:
    """Domain service for resolving file naming conflicts."""

    @staticmethod
    def resolve_naming_conflict(
        primary_file: MediaFile,
        conflicting_files: list[MediaFile],
    ) -> dict[MediaFile, FilePath]:
        results = {}
        results[primary_file] = FilePath(primary_file.path.directory, f"{primary_file.path.stem}.txt")
        for file in conflicting_files:
            if file.media_type == MediaType.IMAGE:
                results[file] = FilePath(file.path.directory, f"{file.path.stem}_images.txt")
        return results
```

**`FileGroupingStrategy`** (Domain Service):

```python
class FileGroupingStrategy:
    @staticmethod
    def group_by_stem(files: list[MediaFile]) -> dict[str, list[MediaFile]]:
        groups: dict[str, list[MediaFile]] = defaultdict(list)
        for file in files:
            groups[file.path.stem.lower()].append(file)
        for stem in groups:
            groups[stem].sort(key=lambda f: f.get_processing_priority())
        return dict(groups)
```

### **Repositories**

**`MediaFileRepository`** (Interface):

```python
class MediaFileRepository(ABC):
    @abstractmethod
    def find_by_path(self, path: FilePath) -> MediaFile | None: ...

    @abstractmethod
    def find_by_directory(self, directory: Path) -> list[MediaFile]: ...

    @abstractmethod
    def save(self, media_file: MediaFile) -> None: ...
```

**`FileSystemMediaFileRepository`** (Implementation):

```python
class FileSystemMediaFileRepository(MediaFileRepository):
    def __init__(self, config: PipelineConfig):
        self.config = config

    def find_by_directory(self, directory: Path) -> list[MediaFile]:
        media_files = []
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                media_type = MediaType.from_extension(file_path.suffix)
                if media_type:
                    media_files.append(
                        MediaFile(
                            file_id=str(uuid.uuid4()),
                            path=FilePath.from_path(file_path),
                            media_type=media_type,
                        )
                    )
        return media_files
```

### **Aggregates**

**`MediaProcessingAggregate`** (Aggregate Root):

```python
class MediaProcessingAggregate:
    def __init__(self, media_file: MediaFile):
        self.media_file = media_file
        self.transcript: Transcript | None = None
        self.study_material: StudyMaterial | None = None
        self._domain_events: list[DomainEvent] = []

    def transcribe(self, transcription_service: AudioTranscriptionService) -> None:
        if not self.media_file.can_be_transcribed():
            raise DomainError("Media file cannot be transcribed")
        self.transcript = transcription_service.transcribe(self.media_file)
        self._domain_events.append(TranscriptCreatedEvent(self.transcript))

    def generate_study_material(self, llm_service: LLMGenerationService) -> None:
        if not self.transcript or not self.transcript.can_generate_study_material():
            raise DomainError("Cannot generate study material without a valid transcript")
        self.study_material = llm_service.generate_study_material(self.transcript)
        self._domain_events.append(StudyMaterialCreatedEvent(self.study_material))

    def get_domain_events(self) -> list[DomainEvent]:
        return self._domain_events.copy()
```

### **Migration Strategy**

#### **Phase 1: Introduce Service Layer**

1. Create service interfaces for current processors
2. Extract business logic from processors into services
3. Keep existing processors as service implementations
4. Gradually migrate code to use services

#### **Phase 2: Introduce Domain Model**

1. Create domain entities (`MediaFile`, `Transcript`, `StudyMaterial`)
2. Extract business rules into domain objects
3. Create value objects (`MediaType`, `ProcessingStatus`)
4. Migrate business logic from services to domain objects

#### **Phase 3: Introduce Repositories**

1. Create repository interfaces
2. Implement file system repositories
3. Replace direct file access with repository calls
4. Enable easy swapping of storage backends

#### **Phase 4: Refactor Application Services**

1. Create application services that orchestrate domain services
2. Move orchestration logic from `pipeline.py` into application services
3. Use domain events for cross-aggregate communication
4. Implement proper transaction boundaries

### **Benefits of DDD**

1. **Ubiquitous Language**: Code uses domain terms that match business language
2. **Rich Domain Model**: Business logic is encapsulated in domain objects
3. **Testability**: Domain logic can be tested without infrastructure dependencies
4. **Maintainability**: Changes to business rules are localized to the domain layer
5. **Clarity**: Domain concepts are explicit and well-defined
6. **Flexibility**: Infrastructure can be swapped without affecting domain logic

### **Combined SOA + DDD Architecture**

```text
┌─────────────────────────────────────────────────────────────┐
│              Presentation Layer (CLI, API, Web)             │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│         Application Services (Orchestration)                │
│  - TranscriptionOrchestrationService                        │
│  - StudyMaterialGenerationService                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│              Domain Layer (Business Logic)                  │
│  Entities: MediaFile, Transcript, StudyMaterial             │
│  Value Objects: MediaType, ProcessingStatus                 │
│  Domain Services: ConflictResolver, FileGroupingStrategy    │
│  Aggregates: MediaProcessingAggregate                       │
│  Repositories: MediaFileRepository (interface)              │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│         Infrastructure Layer (Technical Details)            │
│  - FileSystemMediaFileRepository (implements Repository)    │
│  - FileStorageService                                       │
│  - PDFGenerationService                                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│         External Services (Third-party APIs)                │
│  - WhisperService                                           │
│  - TesseractService                                         │
│  - OllamaService                                            │
└─────────────────────────────────────────────────────────────┘
```

**Key Principles**:

1. **Dependency Inversion**: Domain layer has no infrastructure dependencies
2. **Service Contracts**: Clear interfaces between all layers
3. **Domain Events**: Loose coupling between aggregates via events
4. **Repository Pattern**: Persistence abstracted behind repository interfaces
5. **Value Objects**: Immutable objects for domain concepts

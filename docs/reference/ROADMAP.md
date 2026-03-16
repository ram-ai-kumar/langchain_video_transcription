# Architecture Roadmap

[← Back to docs](../README.md)

This document describes the long-term architectural evolution path for the platform. It is separated from the [immediate task list](./TODO.md) to keep day-to-day work focused.

---

## Architecture Evolution: Service-Oriented Architecture (SOA)

### Current Architecture Limitations

While the current architecture is well-structured, it has some limitations:

1. **Tight Coupling**: Processors directly depend on infrastructure (Whisper, Tesseract, Pandoc)
2. **Limited Scalability**: Monolithic design makes independent scaling difficult
3. **Infrastructure Leakage**: File paths, external tool calls, and technical details are mixed with business logic
4. **Limited Testability**: Hard to mock external dependencies and test business rules in isolation
5. **No Clear Service Boundaries**: Functionality is grouped by technical concerns rather than business capabilities

### Proposed SOA Structure

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

### Key Services

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

### Benefits of SOA

1. **Loose Coupling**: Services communicate through well-defined interfaces
2. **Reusability**: Services can be reused across different applications
3. **Testability**: Easy to mock service interfaces for unit testing
4. **Scalability**: Services can be scaled independently
5. **Maintainability**: Changes to one service don't affect others
6. **Technology Independence**: Can swap implementations without changing interfaces

---

## Architecture Evolution: Domain-Driven Design (DDD)

DDD focuses on **modeling the business domain** using domain concepts, entities, value objects, and aggregates.

### Domain Model Structure

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

### Domain Entities

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

### Value Objects

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

### Domain Services

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

### Repositories

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

### Aggregates

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

### Migration Strategy

#### Phase 1: Introduce Service Layer

1. Create service interfaces for current processors
2. Extract business logic from processors into services
3. Keep existing processors as service implementations
4. Gradually migrate code to use services

#### Phase 2: Introduce Domain Model

1. Create domain entities (`MediaFile`, `Transcript`, `StudyMaterial`)
2. Extract business rules into domain objects
3. Create value objects (`MediaType`, `ProcessingStatus`)
4. Migrate business logic from services to domain objects

#### Phase 3: Introduce Repositories

1. Create repository interfaces
2. Implement file system repositories
3. Replace direct file access with repository calls
4. Enable easy swapping of storage backends

#### Phase 4: Refactor Application Services

1. Create application services that orchestrate domain services
2. Move orchestration logic from `pipeline.py` into application services
3. Use domain events for cross-aggregate communication
4. Implement proper transaction boundaries

### Benefits of DDD

1. **Ubiquitous Language**: Code uses domain terms that match business language
2. **Rich Domain Model**: Business logic is encapsulated in domain objects
3. **Testability**: Domain logic can be tested without infrastructure dependencies
4. **Maintainability**: Changes to business rules are localized to the domain layer
5. **Clarity**: Domain concepts are explicit and well-defined
6. **Flexibility**: Infrastructure can be swapped without affecting domain logic

### Combined SOA + DDD Architecture

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

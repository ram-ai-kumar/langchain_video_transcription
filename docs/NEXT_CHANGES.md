# Next Changes: Upcoming Architecture Evolution

[← Back to README](../README.md)

This document describes **planned architecture evolution** for the Video Transcription & Study Material Generator. It outlines how the codebase may be improved with **Service-Oriented Architecture (SOA)** and **Domain-Driven Design (DDD)** in future releases. These are forward-looking proposals, not current implementation.

---

## Architecture Evolution: Service-Oriented Architecture & Domain-Driven Design

### **Current Architecture Limitations**

While the current architecture is well-structured, it has some limitations that could be addressed with **Service-Oriented Architecture (SOA)** and **Domain-Driven Design (DDD)**:

1. **Tight Coupling**: Processors directly depend on infrastructure (Whisper, Tesseract, Pandoc)
2. **Anemic Domain Model**: Business logic is scattered across processors rather than encapsulated in domain objects
3. **Infrastructure Leakage**: File paths, external tool calls, and technical details are mixed with business logic
4. **Limited Testability**: Hard to mock external dependencies and test business rules in isolation
5. **No Domain Language**: Code uses technical terms rather than domain concepts (e.g., "processor" vs "transcription service")
6. **Missing Abstractions**: No clear service boundaries or domain boundaries

### **Proposed Architecture: SOA + DDD**

The following sections outline how to evolve the architecture using SOA and DDD principles.

---

### **1. Service-Oriented Architecture (SOA)**

SOA organizes functionality into **loosely coupled, reusable services** with well-defined interfaces. Each service encapsulates a specific business capability.

#### **Service Layer Structure**

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
│ Domain       │ │ Infrastructure│ │ External   │
│ Services     │ │ Services      │ │ Services   │
│              │ │              │ │            │
│ - Audio      │ │ - File       │ │ - Whisper  │
│   Transcription│ │   Storage    │ │ - Tesseract│
│ - OCR        │ │ - PDF        │ │ - Ollama   │
│ - LLM        │ │   Generation  │ │            │
│   Generation │ │              │ │            │
└──────────────┘ └──────────────┘ └────────────┘
```

#### **Key Services**

**Application Services** (Orchestration Layer):

- **`TranscriptionOrchestrationService`**:
  - Coordinates the entire transcription workflow
  - Manages three-pass processing
  - Handles file grouping and conflict resolution
  - Delegates to domain services for business logic

- **`StudyMaterialGenerationService`**:
  - Orchestrates study material creation
  - Coordinates LLM processing and PDF generation
  - Manages output file paths

- **`MediaProcessingService`**:
  - Handles media type detection
  - Routes to appropriate domain services
  - Manages processing priority

**Domain Services** (Business Logic Layer):

- **`AudioTranscriptionService`**:
  - Interface: `transcribe_audio(audio_file: AudioFile) -> Transcript`
  - Encapsulates transcription business rules
  - Delegates to infrastructure for actual transcription

- **`OCRService`**:
  - Interface: `extract_text(images: List[ImageFile]) -> Transcript`
  - Handles OCR business logic
  - Manages batch processing rules

- **`LLMGenerationService`**:
  - Interface: `generate_study_material(transcript: Transcript) -> StudyMaterial`
  - Encapsulates prompt engineering logic
  - Manages LLM interaction patterns

**Infrastructure Services** (Technical Layer):

- **`FileStorageService`**:
  - Interface: `save_file(content: bytes, path: Path)`, `read_file(path: Path) -> bytes`
  - Abstracts file system operations
  - Enables testing with in-memory storage

- **`PDFGenerationService`**:
  - Interface: `generate_pdf(markdown: str, output_path: Path) -> PDF`
  - Abstracts PDF generation details
  - Handles engine fallback logic

**External Services** (Integration Layer):

- **`WhisperService`**: Wraps Whisper API calls
- **`TesseractService`**: Wraps Tesseract OCR calls
- **`OllamaService`**: Wraps Ollama LLM API calls

#### **Benefits of SOA**

1. **Loose Coupling**: Services communicate through well-defined interfaces
2. **Reusability**: Services can be reused across different applications
3. **Testability**: Easy to mock service interfaces for unit testing
4. **Scalability**: Services can be scaled independently
5. **Maintainability**: Changes to one service don't affect others
6. **Technology Independence**: Can swap implementations without changing interfaces

---

### **2. Domain-Driven Design (DDD)**

DDD focuses on **modeling the business domain** using domain concepts, entities, value objects, and aggregates.

#### **Domain Model Structure**

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

#### **Domain Entities**

**`MediaFile`** (Entity):

```python
class MediaFile:
    """Domain entity representing a media file."""

    def __init__(self, file_id: str, path: FilePath, media_type: MediaType):
        self.file_id = file_id  # Unique identifier
        self.path = path  # Value object
        self.media_type = media_type  # Value object
        self.metadata: Dict[str, Any] = {}

    def can_be_transcribed(self) -> bool:
        """Business rule: Can this file be transcribed?"""
        return self.media_type in [MediaType.AUDIO, MediaType.VIDEO]

    def get_processing_priority(self) -> int:
        """Business rule: Priority for processing (video > audio > text > image)."""
        priority_map = {
            MediaType.VIDEO: 1,
            MediaType.AUDIO: 2,
            MediaType.TEXT: 3,
            MediaType.IMAGE: 4
        }
        return priority_map.get(self.media_type, 999)
```

**`Transcript`** (Entity):

```python
class Transcript:
    """Domain entity representing a transcript."""

    def __init__(self, transcript_id: str, content: TranscriptContent, source: MediaFile):
        self.transcript_id = transcript_id
        self.content = content  # Value object
        self.source = source
        self.created_at: datetime = datetime.now()
        self.status: ProcessingStatus = ProcessingStatus.CREATED

    def is_empty(self) -> bool:
        """Business rule: Is transcript empty?"""
        return self.content.is_empty()

    def can_generate_study_material(self) -> bool:
        """Business rule: Can we generate study material from this transcript?"""
        return not self.is_empty() and self.status == ProcessingStatus.COMPLETED
```

**`StudyMaterial`** (Entity):

```python
class StudyMaterial:
    """Domain entity representing generated study material."""

    def __init__(self, material_id: str, content: StudyMaterialContent, transcript: Transcript):
        self.material_id = material_id
        self.content = content  # Value object
        self.transcript = transcript
        self.pdf_path: Optional[FilePath] = None
        self.created_at: datetime = datetime.now()
```

#### **Value Objects**

**`MediaType`** (Value Object):

```python
@dataclass(frozen=True)
class MediaType:
    """Immutable value object representing media type."""

    name: str
    extensions: Tuple[str, ...]

    VIDEO = MediaType("video", (".mp4", ".mkv", ".avi", ".mov"))
    AUDIO = MediaType("audio", (".mp3", ".wav", ".m4a", ".aac"))
    TEXT = MediaType("text", (".txt",))
    IMAGE = MediaType("image", (".png", ".jpg", ".jpeg", ".gif"))

    @classmethod
    def from_extension(cls, ext: str) -> Optional['MediaType']:
        """Factory method: Create from file extension."""
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
    """Immutable value object representing processing status."""

    value: str

    PENDING = ProcessingStatus("pending")
    IN_PROGRESS = ProcessingStatus("in_progress")
    COMPLETED = ProcessingStatus("completed")
    FAILED = ProcessingStatus("failed")
    SKIPPED = ProcessingStatus("skipped")
```

#### **Domain Services**

**`ConflictResolver`** (Domain Service):

```python
class ConflictResolver:
    """Domain service for resolving file naming conflicts."""

    @staticmethod
    def resolve_naming_conflict(
        primary_file: MediaFile,
        conflicting_files: List[MediaFile]
    ) -> Dict[MediaFile, FilePath]:
        """Business rule: Resolve naming conflicts for mixed media."""
        results = {}

        # Primary file gets standard name
        results[primary_file] = FilePath(
            primary_file.path.directory,
            f"{primary_file.path.stem}.txt"
        )

        # Conflicting images get suffixed name
        for file in conflicting_files:
            if file.media_type == MediaType.IMAGE:
                results[file] = FilePath(
                    file.path.directory,
                    f"{file.path.stem}_images.txt"
                )

        return results
```

**`FileGroupingStrategy`** (Domain Service):

```python
class FileGroupingStrategy:
    """Domain service for grouping files by business rules."""

    @staticmethod
    def group_by_stem(files: List[MediaFile]) -> Dict[str, List[MediaFile]]:
        """Business rule: Group files by stem (filename without extension)."""
        groups = defaultdict(list)

        for file in files:
            stem = file.path.stem.lower()  # Case-insensitive grouping
            groups[stem].append(file)

        # Sort files within each group by priority
        for stem in groups:
            groups[stem].sort(key=lambda f: f.get_processing_priority())

        return dict(groups)
```

#### **Repositories**

**`MediaFileRepository`** (Repository Interface):

```python
class MediaFileRepository(ABC):
    """Repository interface for MediaFile persistence."""

    @abstractmethod
    def find_by_path(self, path: FilePath) -> Optional[MediaFile]:
        """Find media file by path."""
        pass

    @abstractmethod
    def find_by_directory(self, directory: Path) -> List[MediaFile]:
        """Find all media files in directory."""
        pass

    @abstractmethod
    def save(self, media_file: MediaFile) -> None:
        """Save media file."""
        pass
```

**`FileSystemMediaFileRepository`** (Repository Implementation):

```python
class FileSystemMediaFileRepository(MediaFileRepository):
    """File system implementation of MediaFileRepository."""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def find_by_directory(self, directory: Path) -> List[MediaFile]:
        """Discover media files from file system."""
        media_files = []

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                media_type = MediaType.from_extension(file_path.suffix)
                if media_type:
                    media_file = MediaFile(
                        file_id=str(uuid.uuid4()),
                        path=FilePath.from_path(file_path),
                        media_type=media_type
                    )
                    media_files.append(media_file)

        return media_files
```

#### **Aggregates**

**`MediaProcessingAggregate`** (Aggregate Root):

```python
class MediaProcessingAggregate:
    """Aggregate root for media processing operations."""

    def __init__(self, media_file: MediaFile):
        self.media_file = media_file
        self.transcript: Optional[Transcript] = None
        self.study_material: Optional[StudyMaterial] = None
        self._domain_events: List[DomainEvent] = []

    def transcribe(self, transcription_service: AudioTranscriptionService) -> None:
        """Business operation: Transcribe media file."""
        if not self.media_file.can_be_transcribed():
            raise DomainError("Media file cannot be transcribed")

        self.transcript = transcription_service.transcribe(self.media_file)
        self._domain_events.append(TranscriptCreatedEvent(self.transcript))

    def generate_study_material(
        self,
        llm_service: LLMGenerationService
    ) -> None:
        """Business operation: Generate study material from transcript."""
        if not self.transcript or not self.transcript.can_generate_study_material():
            raise DomainError("Cannot generate study material")

        self.study_material = llm_service.generate_study_material(self.transcript)
        self._domain_events.append(StudyMaterialCreatedEvent(self.study_material))

    def get_domain_events(self) -> List[DomainEvent]:
        """Return domain events for event sourcing."""
        return self._domain_events.copy()
```

#### **Benefits of DDD**

1. **Ubiquitous Language**: Code uses domain terms that match business language
2. **Rich Domain Model**: Business logic is encapsulated in domain objects
3. **Testability**: Domain logic can be tested without infrastructure
4. **Maintainability**: Changes to business rules are localized to domain layer
5. **Clarity**: Domain concepts are explicit and well-defined
6. **Flexibility**: Can change infrastructure without affecting domain logic

---

### **3. Combined Architecture: SOA + DDD**

Combining SOA and DDD creates a powerful architecture:

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
│  Entities: MediaFile, Transcript, StudyMaterial            │
│  Value Objects: MediaType, ProcessingStatus                 │
│  Domain Services: ConflictResolver, FileGroupingStrategy     │
│  Aggregates: MediaProcessingAggregate                        │
│  Repositories: MediaFileRepository (interface)             │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│         Infrastructure Layer (Technical Details)             │
│  - FileSystemMediaFileRepository (implements Repository)    │
│  - FileStorageService                                       │
│  - PDFGenerationService                                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│         External Services (Third-party APIs)                │
│  - WhisperService                                           │
│  - TesseractService                                         │
│  - OllamaService                                             │
└─────────────────────────────────────────────────────────────┘
```

#### **Key Principles**

1. **Dependency Inversion**: Domain layer doesn't depend on infrastructure
2. **Service Contracts**: Clear interfaces between layers
3. **Domain Events**: Use events for loose coupling between aggregates
4. **Repository Pattern**: Abstract persistence behind repository interfaces
5. **Value Objects**: Use immutable value objects for domain concepts

---

### **4. Migration Strategy**

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
2. Move orchestration logic from pipeline to application services
3. Use domain events for cross-aggregate communication
4. Implement proper transaction boundaries

---

### **5. Example: Refactored Code**

#### **Before (Current Architecture)**

```python
# Current: Processor directly uses infrastructure
class AudioProcessor(BaseProcessor):
    def process(self, audio_path: Path, transcript_path: Path) -> ProcessResult:
        model = whisper.load_model(self.config.whisper_model)
        result = model.transcribe(str(audio_path))
        with open(transcript_path, "w") as f:
            f.write(result["text"])
        return ProcessResult(success=True, ...)
```

#### **After (SOA + DDD)**

```python
# Domain Entity
class MediaFile:
    def __init__(self, file_id: str, path: FilePath, media_type: MediaType):
        self.file_id = file_id
        self.path = path
        self.media_type = media_type

# Domain Service Interface
class AudioTranscriptionService(ABC):
    @abstractmethod
    def transcribe(self, media_file: MediaFile) -> Transcript:
        pass

# Domain Service Implementation
class WhisperTranscriptionService(AudioTranscriptionService):
    def __init__(self, whisper_client: WhisperService, config: Config):
        self.whisper_client = whisper_client
        self.config = config

    def transcribe(self, media_file: MediaFile) -> Transcript:
        if not media_file.can_be_transcribed():
            raise DomainError("Cannot transcribe this media type")

        audio_content = self.whisper_client.transcribe(media_file.path)
        return Transcript(
            transcript_id=str(uuid.uuid4()),
            content=TranscriptContent(audio_content),
            source=media_file
        )

# Application Service
class TranscriptionOrchestrationService:
    def __init__(
        self,
        transcription_service: AudioTranscriptionService,
        repository: TranscriptRepository
    ):
        self.transcription_service = transcription_service
        self.repository = repository

    def process_media_file(self, media_file: MediaFile) -> Transcript:
        transcript = self.transcription_service.transcribe(media_file)
        self.repository.save(transcript)
        return transcript
```

---

### **6. Benefits Summary**

#### **Service-Oriented Architecture Benefits**

- ✅ **Loose Coupling**: Services communicate through interfaces
- ✅ **Reusability**: Services can be reused across applications
- ✅ **Testability**: Easy to mock and test services independently
- ✅ **Scalability**: Services can be scaled independently
- ✅ **Technology Independence**: Swap implementations without changing interfaces

#### **Domain-Driven Design Benefits**

- ✅ **Ubiquitous Language**: Code matches business terminology
- ✅ **Rich Domain Model**: Business logic encapsulated in domain objects
- ✅ **Testability**: Domain logic testable without infrastructure
- ✅ **Maintainability**: Business rule changes localized to domain layer
- ✅ **Clarity**: Domain concepts are explicit and well-defined
- ✅ **Flexibility**: Change infrastructure without affecting domain logic

#### **Combined Benefits**

- ✅ **Separation of Concerns**: Clear boundaries between layers
- ✅ **Business Focus**: Domain layer focuses on business rules
- ✅ **Technical Flexibility**: Infrastructure can be swapped easily
- ✅ **Testability**: Each layer can be tested independently
- ✅ **Maintainability**: Changes are localized to appropriate layers
- ✅ **Extensibility**: Easy to add new services or domain concepts

---

### **7. Test Coverage Strategy**

#### **Current Test Coverage Limitations**

The current codebase has minimal test coverage, which presents several challenges:

1. **No Unit Tests**: Core business logic in processors is untested
2. **Integration Gaps**: No tests for end-to-end workflows
3. **External Dependencies**: Hard to test without actual Whisper/Tesseract/Ollama
4. **Regression Risk**: Changes can break existing functionality silently
5. **Refactoring Barriers**: Fear of breaking code prevents architecture improvements

#### **Proposed Test Coverage Architecture**

A comprehensive testing strategy aligned with SOA and DDD principles:

```text
Testing Pyramid
┌─────────────────────────────────────────────────────────────┐
│                    E2E Tests (5%)                           │
│  - Full workflow testing                                    │
│  - Integration with real external services                   │
│  - User scenario validation                                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                Integration Tests (15%)                       │
│  - Service layer integration                                 │
│  - Repository implementations                               │
│  - External service integrations                            │
│  - Database/file system interactions                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  Unit Tests (80%)                           │
│  - Domain entities and value objects                        │
│  - Domain services                                          │
│  - Application services                                     │
│  - Business logic validation                                │
└─────────────────────────────────────────────────────────────┘
```

#### **Domain Layer Testing**

**Entity Tests**:

```python
class TestMediaFile:
    """Unit tests for MediaFile domain entity."""

    def test_can_be_transcribed_audio(self):
        media_file = MediaFile(
            file_id="test-1",
            path=FilePath("/test/audio.mp3"),
            media_type=MediaType.AUDIO
        )
        assert media_file.can_be_transcribed() is True

    def test_can_be_transcribed_image(self):
        media_file = MediaFile(
            file_id="test-2",
            path=FilePath("/test/image.png"),
            media_type=MediaType.IMAGE
        )
        assert media_file.can_be_transcribed() is False

    def test_processing_priority_video_highest(self):
        video_file = MediaFile(
            file_id="test-3",
            path=FilePath("/test/video.mp4"),
            media_type=MediaType.VIDEO
        )
        assert video_file.get_processing_priority() == 1

class TestTranscript:
    """Unit tests for Transcript domain entity."""

    def test_empty_transcript_detection(self):
        empty_content = TranscriptContent("")
        transcript = Transcript(
            transcript_id="test-1",
            content=empty_content,
            source=mock_media_file
        )
        assert transcript.is_empty() is True

    def test_study_material_generation_eligibility(self):
        content = TranscriptContent("Valid transcript content")
        transcript = Transcript(
            transcript_id="test-2",
            content=content,
            source=mock_media_file
        )
        transcript.status = ProcessingStatus.COMPLETED
        assert transcript.can_generate_study_material() is True
```

**Value Object Tests**:

```python
class TestMediaType:
    """Unit tests for MediaType value object."""

    @pytest.mark.parametrize("extension,expected", [
        (".mp4", MediaType.VIDEO),
        (".mp3", MediaType.AUDIO),
        (".txt", MediaType.TEXT),
        (".png", MediaType.IMAGE),
        (".unknown", None)
    ])
    def test_from_extension(self, extension, expected):
        result = MediaType.from_extension(extension)
        assert result == expected

    def test_media_type_immutability(self):
        video_type = MediaType.VIDEO
        with pytest.raises(FrozenInstanceError):
            video_type.name = "changed"
```

**Domain Service Tests**:

```python
class TestConflictResolver:
    """Unit tests for ConflictResolver domain service."""

    def test_resolve_naming_conflict_mixed_media(self):
        primary_file = MediaFile(
            file_id="primary",
            path=FilePath("/test/lecture.mp4"),
            media_type=MediaType.VIDEO
        )
        conflicting_image = MediaFile(
            file_id="conflict",
            path=FilePath("/test/lecture.png"),
            media_type=MediaType.IMAGE
        )

        resolutions = ConflictResolver.resolve_naming_conflict(
            primary_file, [conflicting_image]
        )

        assert resolutions[primary_file].name == "lecture.txt"
        assert resolutions[conflicting_image].name == "lecture_images.txt"

class TestFileGroupingStrategy:
    """Unit tests for FileGroupingStrategy domain service."""

    def test_group_by_stem_case_insensitive(self):
        files = [
            MediaFile("1", FilePath("/test/Lecture.mp4"), MediaType.VIDEO),
            MediaFile("2", FilePath("/test/lecture.MP3"), MediaType.AUDIO),
            MediaFile("3", FilePath("/test/LECTURE.png"), MediaType.IMAGE)
        ]

        groups = FileGroupingStrategy.group_by_stem(files)

        assert "lecture" in groups
        assert len(groups["lecture"]) == 3
        # Verify priority ordering
        assert groups["lecture"][0].media_type == MediaType.VIDEO
```

#### **Service Layer Testing**

**Domain Service Tests with Mocks**:

```python
class TestAudioTranscriptionService:
    """Unit tests for AudioTranscriptionService."""

    def test_transcribe_audio_success(self, mock_whisper_service):
        service = WhisperTranscriptionService(
            whisper_client=mock_whisper_service,
            config=test_config
        )

        media_file = MediaFile(
            file_id="test-1",
            path=FilePath("/test/audio.mp3"),
            media_type=MediaType.AUDIO
        )

        mock_whisper_service.transcribe.return_value = "Test transcript"

        transcript = service.transcribe(media_file)

        assert isinstance(transcript, Transcript)
        assert transcript.content.value == "Test transcript"
        assert transcript.source == media_file
        mock_whisper_service.transcribe.assert_called_once_with(media_file.path)

    def test_transcribe_unsupported_media_type(self, mock_whisper_service):
        service = WhisperTranscriptionService(
            whisper_client=mock_whisper_service,
            config=test_config
        )

        image_file = MediaFile(
            file_id="test-2",
            path=FilePath("/test/image.png"),
            media_type=MediaType.IMAGE
        )

        with pytest.raises(DomainError, match="Cannot transcribe this media type"):
            service.transcribe(image_file)
```

**Application Service Tests**:

```python
class TestTranscriptionOrchestrationService:
    """Unit tests for TranscriptionOrchestrationService."""

    def test_process_media_file_success(self, mock_transcription_service, mock_repository):
        service = TranscriptionOrchestrationService(
            transcription_service=mock_transcription_service,
            repository=mock_repository
        )

        media_file = MediaFile(
            file_id="test-1",
            path=FilePath("/test/audio.mp3"),
            media_type=MediaType.AUDIO
        )

        expected_transcript = Transcript(
            transcript_id="transcript-1",
            content=TranscriptContent("Test content"),
            source=media_file
        )

        mock_transcription_service.transcribe.return_value = expected_transcript

        result = service.process_media_file(media_file)

        assert result == expected_transcript
        mock_transcription_service.transcribe.assert_called_once_with(media_file)
        mock_repository.save.assert_called_once_with(expected_transcript)
```

#### **Infrastructure Layer Testing**

**Repository Tests**:

```python
class TestFileSystemMediaFileRepository:
    """Integration tests for FileSystemMediaFileRepository."""

    def test_find_by_directory_discovers_media_files(self, tmp_path):
        # Create test files
        (tmp_path / "video.mp4").touch()
        (tmp_path / "audio.mp3").touch()
        (tmp_path / "document.txt").touch()
        (tmp_path / "image.png").touch()
        (tmp_path / "unsupported.xyz").touch()

        repository = FileSystemMediaFileRepository(test_config)
        media_files = repository.find_by_directory(tmp_path)

        assert len(media_files) == 4  # Excludes .xyz file

        media_types = [f.media_type for f in media_files]
        assert MediaType.VIDEO in media_types
        assert MediaType.AUDIO in media_types
        assert MediaType.TEXT in media_types
        assert MediaType.IMAGE in media_types
```

#### **Integration Testing**

**Service Integration Tests**:

```python
class TestTranscriptionWorkflow:
    """Integration tests for complete transcription workflow."""

    @pytest.mark.integration
    def test_end_to_end_audio_transcription(self, tmp_path):
        # Setup real Whisper service (or test double)
        whisper_service = WhisperService(model_size="tiny")
        repository = FileSystemMediaFileRepository(test_config)
        transcription_service = WhisperTranscriptionService(whisper_service, test_config)
        orchestration_service = TranscriptionOrchestrationService(
            transcription_service=transcription_service,
            repository=repository
        )

        # Create test audio file
        audio_file_path = tmp_path / "test_audio.wav"
        generate_test_audio_file(audio_file_path)

        media_file = MediaFile(
            file_id="test-1",
            path=FilePath.from_path(audio_file_path),
            media_type=MediaType.AUDIO
        )

        transcript = orchestration_service.process_media_file(media_file)

        assert isinstance(transcript, Transcript)
        assert not transcript.is_empty()
        assert transcript.status == ProcessingStatus.COMPLETED
```

#### **End-to-End Testing**

**CLI E2E Tests**:

```python
class TestCLIEndToEnd:
    """End-to-end tests for CLI interface."""

    @pytest.mark.e2e
    def test_full_transcription_and_study_generation(self, tmp_path, runner):
        # Setup test data
        video_path = tmp_path / "lecture.mp4"
        create_test_video_file(video_path)

        # Run CLI command
        result = runner.invoke([
            "process", str(video_path),
            "--output", str(tmp_path),
            "--generate-study"
        ])

        assert result.exit_code == 0

        # Verify outputs
        transcript_path = tmp_path / "lecture.txt"
        study_material_path = tmp_path / "lecture_study.pdf"

        assert transcript_path.exists()
        assert study_material_path.exists()

        # Verify content
        transcript_content = transcript_path.read_text()
        assert len(transcript_content) > 0
```

#### **Test Coverage Goals**

**Coverage Targets by Layer**:

- **Domain Layer**: 95%+ coverage
  - Entities: 100%
  - Value Objects: 100%
  - Domain Services: 90%+
- **Service Layer**: 85%+ coverage
  - Domain Services: 90%+
  - Application Services: 85%+
- **Infrastructure Layer**: 80%+ coverage
  - Repositories: 85%+
  - External Service Wrappers: 75%+
- **Presentation Layer**: 70%+ coverage
  - CLI Commands: 80%+
  - API Endpoints: 75%+

#### **Testing Tools and Infrastructure**

**Core Testing Stack**:

```python
# pytest.ini
[tool:pytest]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov=src",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=80"
]
markers = [
    "unit: Unit tests (fast, no external dependencies)",
    "integration: Integration tests (requires external services)",
    "e2e: End-to-end tests (full workflow)",
    "slow: Tests that take longer than 1 second"
]
```

**Test Utilities**:

```python
# tests/fixtures.py
@pytest.fixture
def mock_whisper_service():
    """Mock Whisper service for unit tests."""
    with patch('src.services.whisper.WhisperService') as mock:
        mock.transcribe.return_value = "Mock transcript content"
        yield mock

@pytest.fixture
def test_media_file():
    """Standard test media file."""
    return MediaFile(
        file_id="test-1",
        path=FilePath("/test/audio.mp3"),
        media_type=MediaType.AUDIO
    )

@pytest.fixture
def tmp_path_with_media(tmp_path):
    """Temporary directory with test media files."""
    (tmp_path / "video.mp4").touch()
    (tmp_path / "audio.mp3").touch()
    (tmp_path / "image.png").touch()
    return tmp_path
```

#### **Continuous Integration Testing**

**GitHub Actions Workflow**:

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    services:
      ollama:
        image: ollama/ollama
        ports:
          - 11434:11434

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run unit tests
      run: pytest -m "unit" --cov=src

    - name: Run integration tests
      run: pytest -m "integration"
      env:
        OLLAMA_HOST: http://localhost:11434

    - name: Run E2E tests
      run: pytest -m "e2e"
      if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

#### **Test Coverage Benefits**

**Immediate Benefits**:

- ✅ **Regression Prevention**: Catch breaking changes early
- ✅ **Refactoring Confidence**: Safely improve architecture
- ✅ **Documentation**: Tests serve as living documentation
- ✅ **Design Feedback**: Writing tests improves API design

**Long-term Benefits**:

- ✅ **Maintenance Efficiency**: Quickly identify and fix issues
- ✅ **Team Velocity**: Reduce time spent on manual testing
- ✅ **Code Quality**: Enforce consistent coding standards
- ✅ **Architecture Evolution**: Safely implement SOA/DDD changes

---

### **8. When to Apply SOA + DDD**

**Consider SOA + DDD when:**

- ✅ System is growing in complexity
- ✅ Multiple teams are working on the codebase
- ✅ Business rules are complex and frequently changing
- ✅ You need to support multiple interfaces (CLI, API, Web)
- ✅ You want to swap infrastructure components easily
- ✅ You need better testability and maintainability

**Current architecture is sufficient when:**

- ✅ System is simple and stable
- ✅ Single team maintains the codebase
- ✅ Business rules are straightforward
- ✅ Only one interface (CLI) is needed
- ✅ Infrastructure is unlikely to change

---

### **9. Planned Feature Enhancements**

#### **9.1 AI Generated Content Marking System**

To ensure transparency and proper attribution, all AI-generated content will be clearly marked with author identification and acknowledgments.

##### **Watermark and Attribution System**

**Core Requirements**:

1. **AI Generation Watermark**: All generated PDFs will include a visible watermark identifying them as AI-generated content
2. **Author Attribution Footer**: Every page will include `Ram Kumar, saas.expert.ram@gmail.com` in the footer
3. **Acknowledgment Page**: A dedicated final page acknowledging the author and the utility script

##### **Technical Implementation**

**PDF Generation Service Enhancement**:

```python
class EnhancedPDFGenerationService(PDFGenerationService):
    """Enhanced PDF generation with AI content marking."""

    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        self.author_info = AuthorInfo(
            name="Ram Kumar",
            email="saas.expert.ram@gmail.com"
        )

    def generate_study_material_pdf(
        self,
        study_material: StudyMaterial,
        output_path: Path
    ) -> PDF:
        """Generate PDF with AI content marking."""

        # Create base PDF
        base_pdf = super().generate_study_material_pdf(
            study_material, output_path
        )

        # Add AI marking and attribution
        marked_pdf = self._add_ai_marking(base_pdf)
        attributed_pdf = self._add_author_attribution(marked_pdf)
        final_pdf = self._add_acknowledgment_page(attributed_pdf)

        return final_pdf

    def _add_ai_marking(self, pdf: PDF) -> PDF:
        """Add AI-generated watermark to all pages."""
        watermark_text = "AI Generated Content"

        for page in pdf.pages:
            page.add_watermark(
                text=watermark_text,
                position=WatermarkPosition.CENTER,
                opacity=0.3,
                rotation=45,
                font_size=48,
                color=Color.LIGHT_GRAY
            )

        return pdf

    def _add_author_attribution(self, pdf: PDF) -> PDF:
        """Add author attribution footer to all pages."""
        footer_text = f"Ram Kumar, {self.author_info.email}"

        for page in pdf.pages:
            page.add_footer(
                text=footer_text,
                position=FooterPosition.BOTTOM_RIGHT,
                font_size=10,
                font_style=FontStyle.ITALIC,
                color=Color.DARK_GRAY
            )

        return pdf

    def _add_acknowledgment_page(self, pdf: PDF) -> PDF:
        """Add acknowledgment page as the last page."""
        acknowledgment_content = self._generate_acknowledgment_content()

        acknowledgment_page = PDFPage(
            content=acknowledgment_content,
            page_number=len(pdf.pages) + 1
        )

        pdf.add_page(acknowledgment_page)
        return pdf

    def _generate_acknowledgment_content(self) -> str:
        """Generate acknowledgment page content."""
        return f"""
# Acknowledgment

This study material was generated using an automated utility script created by:

**Ram Kumar**
saas.expert.ram@gmail.com

## About This Utility

This Python-based system demonstrates advanced software engineering principles
in media processing and AI-powered content generation. It seamlessly processes
video, audio, text, and image files to create comprehensive learning materials
including transcripts, summaries, glossaries, and practice questions.

## Technical Features

- **Multi-modal Media Processing**: Supports video, audio, text, and image inputs
- **AI-Powered Content Generation**: Uses state-of-the-art language models
- **Automated PDF Generation**: Creates professionally formatted study materials
- **Intelligent Conflict Resolution**: Handles mixed media file scenarios
- **Object-Oriented Architecture**: Clean, maintainable, and extensible design

## Architecture Highlights

- **Service-Oriented Design**: Loosely coupled, reusable services
- **Domain-Driven Design**: Rich domain model with business logic encapsulation
- **Comprehensive Testing**: High test coverage across all layers
- **Error Handling**: Robust error management and recovery

---

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
```

**Domain Model Extensions**:

```python
@dataclass(frozen=True)
class AuthorInfo:
    """Value object representing author information."""
    name: str
    email: str

    def get_attribution_text(self) -> str:
        return f"{self.name}, {self.email}"

@dataclass(frozen=True)
class WatermarkConfig:
    """Configuration for PDF watermarking."""
    text: str = "AI Generated Content"
    opacity: float = 0.3
    rotation: int = 45
    font_size: int = 48
    color: str = "#CCCCCC"
    position: str = "center"

class AIMarkedPDF(PDF):
    """PDF entity with AI-generated content marking."""

    def __init__(
        self,
        base_pdf: PDF,
        author_info: AuthorInfo,
        watermark_config: WatermarkConfig
    ):
        super().__init__(base_pdf.path)
        self.base_pdf = base_pdf
        self.author_info = author_info
        self.watermark_config = watermark_config
        self._marked = False

    def apply_ai_marking(self) -> None:
        """Apply AI marking to the PDF."""
        if self._marked:
            return

        self._add_watermark()
        self._add_attribution_footer()
        self._add_acknowledgment_page()
        self._marked = True

    def is_ai_marked(self) -> bool:
        """Check if PDF has AI marking."""
        return self._marked
```

#### **9.2 PDF Processing Enhancement**

Extend the pipeline to process existing PDF files for learning content generation, with intelligent detection of AI-generated content.

##### **PDF Content Processing Pipeline**

**Core Requirements**:

1. **PDF Text Extraction**: Extract text content from PDF files
2. **AI-Generated PDF Detection**: Identify and skip previously AI-generated PDFs
3. **Learning Content Generation**: Process extracted text through existing LLM pipeline
4. **Conflict Resolution**: Handle naming conflicts with existing files

##### **PDF Processing Technical Implementation**

**PDF Processing Service**:

```python
class PDFProcessingService(DomainService):
    """Service for processing PDF files and detecting AI-generated content."""

    def __init__(
        self,
        pdf_extractor: PDFTextExtractor,
        ai_detector: AIGeneratedPDFDetector,
        study_material_service: StudyMaterialGenerationService
    ):
        self.pdf_extractor = pdf_extractor
        self.ai_detector = ai_detector
        self.study_material_service = study_material_service

    def process_pdf_file(self, pdf_file: MediaFile) -> ProcessResult:
        """Process a PDF file for learning content generation."""

        # Check if PDF is AI-generated
        if self.ai_detector.is_ai_generated(pdf_file):
            return ProcessResult(
                success=False,
                message="Skipping AI-generated PDF",
                skipped_reason="AI_GENERATED"
            )

        # Extract text content
        try:
            extracted_content = self.pdf_extractor.extract_text(pdf_file.path)

            if extracted_content.is_empty():
                return ProcessResult(
                    success=False,
                    message="PDF contains no extractable text",
                    skipped_reason="EMPTY_CONTENT"
                )

            # Create transcript from extracted content
            transcript = Transcript(
                transcript_id=str(uuid.uuid4()),
                content=TranscriptContent(extracted_content.text),
                source=pdf_file,
                extraction_method=ExtractionMethod.PDF_TEXT
            )

            # Generate study material
            study_material = self.study_material_service.generate_study_material(
                transcript
            )

            return ProcessResult(
                success=True,
                transcript=transcript,
                study_material=study_material
            )

        except Exception as e:
            return ProcessResult(
                success=False,
                message=f"PDF processing failed: {str(e)}",
                error=e
            )

class AIGeneratedPDFDetector(DomainService):
    """Service for detecting AI-generated PDFs."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.ai_markers = [
            "AI Generated Content",
            "Ram Kumar, saas.expert.ram@gmail.com",
            "Acknowledgment",
            "This study material was generated using an automated utility"
        ]

    def is_ai_generated(self, pdf_file: MediaFile) -> bool:
        """Detect if PDF is AI-generated by checking for markers."""

        try:
            # Extract first few pages for analysis
            preview_content = self._extract_preview_content(pdf_file.path)

            # Check for AI generation markers
            marker_count = sum(
                1 for marker in self.ai_markers
                if marker.lower() in preview_content.lower()
            )

            # Consider AI-generated if multiple markers found
            return marker_count >= 2

        except Exception:
            # If we can't analyze, assume it's not AI-generated
            return False

    def _extract_preview_content(self, pdf_path: Path) -> str:
        """Extract content from first few pages for analysis."""
        # Extract text from first 3 pages for marker detection
        pages_to_check = min(3, self._get_page_count(pdf_path))
        content_parts = []

        for page_num in range(pages_to_check):
            page_content = self._extract_page_text(pdf_path, page_num + 1)
            content_parts.append(page_content)

        return " ".join(content_parts)

    def _get_page_count(self, pdf_path: Path) -> int:
        """Get total page count of PDF."""
        # Use PyPDF2 or similar to get page count
        pass

    def _extract_page_text(self, pdf_path: Path, page_num: int) -> str:
        """Extract text from specific page."""
        # Use pdfplumber or similar for text extraction
        pass

class PDFTextExtractor(InfrastructureService):
    """Service for extracting text from PDF files."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.ocr_enabled = config.pdf_ocr_enabled

    def extract_text(self, pdf_path: Path) -> ExtractedContent:
        """Extract text content from PDF file."""

        try:
            # Try direct text extraction first
            text_content = self._extract_direct_text(pdf_path)

            # If direct extraction yields little content, try OCR
            if len(text_content.strip()) < 100 and self.ocr_enabled:
                text_content = self._extract_ocr_text(pdf_path)

            return ExtractedContent(
                text=text_content,
                extraction_method=self._determine_extraction_method(text_content),
                confidence_score=self._calculate_confidence(text_content)
            )

        except Exception as e:
            raise PDFExtractionError(f"Failed to extract text from {pdf_path}: {e}")

    def _extract_direct_text(self, pdf_path: Path) -> str:
        """Extract text directly from PDF using pdfplumber."""
        import pdfplumber

        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n".join(text_parts)

    def _extract_ocr_text(self, pdf_path: Path) -> str:
        """Extract text using OCR when direct extraction fails."""
        # Convert PDF to images and use Tesseract OCR
        pass

    def _determine_extraction_method(self, text: str) -> ExtractionMethod:
        """Determine which extraction method was most effective."""
        if len(text.strip()) > 100:
            return ExtractionMethod.DIRECT_TEXT
        else:
            return ExtractionMethod.OCR

    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score for extracted text."""
        # Simple heuristic based on text length and content quality
        if not text or len(text.strip()) < 50:
            return 0.0

        # Check for meaningful content (words, sentences)
        word_count = len(text.split())
        sentence_count = text.count('.') + text.count('!') + text.count('?')

        confidence = min(1.0, (word_count / 1000) + (sentence_count / 100))
        return confidence

@dataclass(frozen=True)
class ExtractedContent:
    """Value object representing extracted PDF content."""
    text: str
    extraction_method: ExtractionMethod
    confidence_score: float

    def is_empty(self) -> bool:
        return len(self.text.strip()) == 0

    def is_high_quality(self) -> bool:
        return self.confidence_score > 0.7

class ExtractionMethod(Enum):
    """Enumeration of text extraction methods."""
    DIRECT_TEXT = "direct_text"
    OCR = "ocr"
    MIXED = "mixed"
```

**Integration with Existing Pipeline**:

```python
class EnhancedMediaProcessingService(MediaProcessingService):
    """Enhanced media processing service with PDF support."""

    def __init__(
        self,
        audio_service: AudioTranscriptionService,
        ocr_service: OCRService,
        pdf_service: PDFProcessingService,
        conflict_resolver: ConflictResolver
    ):
        super().__init__(audio_service, ocr_service, conflict_resolver)
        self.pdf_service = pdf_service

    def process_media_file(self, media_file: MediaFile) -> ProcessResult:
        """Process media file including PDF support."""

        if media_file.media_type == MediaType.PDF:
            return self.pdf_service.process_pdf_file(media_file)
        else:
            return super().process_media_file(media_file)

    def discover_media_files(self, directory: Path) -> List[MediaFile]:
        """Discover media files including PDFs."""
        media_files = super().discover_media_files(directory)

        # Add PDF files to the discovery
        for pdf_path in directory.rglob("*.pdf"):
            media_file = MediaFile(
                file_id=str(uuid.uuid4()),
                path=FilePath.from_path(pdf_path),
                media_type=MediaType.PDF
            )
            media_files.append(media_file)

        return media_files
```

**File Type Extensions**:

```python
# Extend MediaType value object
@dataclass(frozen=True)
class MediaType:
    """Immutable value object representing media type."""

    name: str
    extensions: Tuple[str, ...]

    VIDEO = MediaType("video", (".mp4", ".mkv", ".avi", ".mov"))
    AUDIO = MediaType("audio", (".mp3", ".wav", ".m4a", ".aac"))
    TEXT = MediaType("text", (".txt",))
    IMAGE = MediaType("image", (".png", ".jpg", ".jpeg", ".gif"))
    PDF = MediaType("pdf", (".pdf",))  # New addition

    @classmethod
    def from_extension(cls, ext: str) -> Optional['MediaType']:
        """Factory method: Create from file extension."""
        ext_lower = ext.lower()
        for media_type in [cls.VIDEO, cls.AUDIO, cls.TEXT, cls.IMAGE, cls.PDF]:
            if ext_lower in media_type.extensions:
                return media_type
        return None
```

#### **Benefits of These Enhancements**

**AI Content Marking Benefits**:

- ✅ **Transparency**: Clear identification of AI-generated content
- ✅ **Attribution**: Proper credit to the author/utility creator
- ✅ **Professionalism**: Consistent branding and acknowledgment
- ✅ **Traceability**: Easy identification of generated materials

**PDF Processing Benefits**:

- ✅ **Extended Capability**: Process existing learning materials
- ✅ **Intelligent Filtering**: Skip AI-generated content to avoid loops
- ✅ **Content Enrichment**: Extract value from existing PDFs
- ✅ **Pipeline Integration**: Seamless integration with existing workflow

#### **Implementation Priority**

#### **Phase 1: AI Content Marking**

1. Implement watermark and attribution system
2. Add acknowledgment page generation
3. Update PDF generation service
4. Add domain model extensions

#### **Phase 2: PDF Processing**

1. Implement PDF text extraction service
2. Create AI-generated PDF detection
3. Integrate with existing media processing pipeline
4. Add comprehensive testing

#### **Phase 3: Integration and Testing**

1. End-to-end workflow testing
2. Performance optimization
3. Error handling and edge cases
4. Documentation updates

#### **9.3 Relative Path Display Enhancement**

Improve terminal output clarity by showing the directory context for processed files, especially during recursive traversal into subfolders.

##### **Relative Path Tracking**

**Core Requirements**:

1. **Base Directory Context**: Consider the initial input folder provided by the user as the "base".
2. **Relative Path Calculation**: Calculate and display folder paths relative to this base.
3. **Traversal Logging**: Show the relative folder path before processing the batch of files contained within it.
4. **Clean Batch Output**: Maintain clean terminal output while providing clear context for deep directory structures.

##### **Technical Implementation**

**Pipeline Enhancement**:

```python
class VideoTranscriptionPipeline:
    # ... existing code ...

    def process_directory(self, directory: Path) -> ProcessResult:
        """Process directory tree with relative path awareness."""
        base_dir = directory.resolve()
        
        # ... discovery and processing logic ...
        
    def _get_relative_path_label(self, current_dir: Path, base_dir: Path) -> str:
        """Calculate relative path for display."""
        try:
            rel_path = current_dir.resolve().relative_to(base_dir)
            if str(rel_path) == ".":
                return "root"
            return str(rel_path)
        except ValueError:
            return current_dir.name

    def _log_folder_context(self, current_dir: Path, base_dir: Path):
        """Log the current directory context being processed."""
        rel_label = self._get_relative_path_label(current_dir, base_dir)
        self.status_reporter.info(f"Entering folder: {rel_label}")
```

#### **Benefits**

- ✅ **Context Awareness**: Users immediately know which part of a complex directory structure is being processed
- ✅ **Improved Logging**: Better traceability for deep recursion
- ✅ **Clean Output**: Standardizes how subfolders are announced in the terminal

---

## Current Issues & Bug Fixes

### **Progress Bar Completion Issue**

#### **Problem Description**

When processing multiple files, progress bars are sometimes left incomplete when the program moves to the next file. This creates a confusing user experience where:

1. **Incomplete Progress Bars**: Previous file progress bars remain partially filled
2. **No Error Indication**: Failed files don't show clear error status in red
3. **Visual Confusion**: Users can't distinguish between completed, failed, and in-progress files

#### **Current Behavior**
```text
[#########-------------------] file1.txt
[##########------------------] file2.mp3
[#######--------------------] file3.png
```

#### **Expected Behavior**
```text
[##########################] file1.txt
[##########################] file2.mp3         Error: Transcription failed (Red colored text)
[##########################] file3.png
```

#### **Root Cause Analysis**

The issue is in the `ProgressReporter.complete_processing()` method in `src/utils/ui_utils.py`:

1. **Missing Completion Call**: When errors occur, `complete_processing(False)` may not be called
2. **Line Management**: Progress bars aren't properly cleared or marked as complete
3. **Error Display**: Failed files don't get red error indicators on the progress line
4. **State Management**: Progress state isn't properly reset between files

#### **Proposed Solution**

##### 1. Ensure Progress Completion

```python
# In pipeline.py - wrap all file processing with try/finally
try:
    self.progress_reporter.start_processing(file_name, steps)
    # ... processing logic ...
    self.progress_reporter.complete_processing(success=True)
except Exception as e:
    self.progress_reporter.complete_processing(success=False)
    self.status_reporter.error(f"Failed to process {file_name}: {e}")
    raise
```

##### 2. Enhanced Progress Display

```python
# In ui_utils.py - improve complete_processing method
def complete_processing(self, success: bool = True) -> None:
    if self.processing:
        self._show_progress()

        progress_line = f"[{self._get_progress_bar()}] {self.current_file}"
        
        if success:
            print(f"\r{progress_line}")
        else:
            # show failed step if available
            step_name = self.steps[self.current_step] if self.current_step < len(self.steps) else "unknown step"
            error_text = f"{progress_line} Error: {step_name} failed"
            print(f"\r{ColorFormatter.error(error_text)}")

        self.processing = False
```

##### 3. Error State Management

```python
# Add error state tracking to ProgressReporter
def __init__(self, verbose: bool = False):
    # ... existing init ...
    self.error_message = None

def set_error(self, message: str) -> None:
    """Set error message for current file."""
    self.error_message = message

def complete_processing(self, success: bool = True) -> None:
    if self.processing:
        self._show_progress()
        
        progress_line = f"[{self._get_progress_bar()}] {self.current_file}"

        if success:
            print(f"\r{progress_line}")
        else:
            step_name = self.steps[self.current_step] if self.current_step < len(self.steps) else "unknown step"
            error_msg = self.error_message or f"{step_name} failed"
            error_line = f"{progress_line} Error: {error_msg}"
            print(f"\r{ColorFormatter.error(error_line)}")

        self.processing = False
        self.error_message = None
```

##### 4. Pipeline Integration

```python
# In pipeline.py - ensure proper error handling
def process_single_source(self, source_path: Path, source_type: str) -> ProcessResult:
    file_name = source_path.name
    steps = PROCESSING_STEPS.get(source_type, ["processing"])

    try:
        self.progress_reporter.start_processing(file_name, steps)

        # ... existing processing logic ...

        self.progress_reporter.complete_processing(success=True)
        return result

    except Exception as e:
        self.progress_reporter.set_error(str(e))
        self.progress_reporter.complete_processing(success=False)
        raise ProcessingError(f"Failed to process {file_name}: {e}")
```

#### **Implementation Steps**

1. **Fix ProgressReporter** - Update `complete_processing()` to show completion status
2. **Add Error Tracking** - Add error message storage and display
3. **Update Pipeline** - Ensure proper try/finally blocks around all processing
4. **Color Entire Line** - Use standard color for success, red for entire failure line
5. **Hide Emojis** - Do not use checkboxes or extra symbols
6. **Test Edge Cases** - Verify behavior with partial failures and interruptions

#### **Files to Modify**

- `src/utils/ui_utils.py` - Enhanced ProgressReporter class
- `src/core/pipeline.py` - Proper error handling and progress completion
- `tests/test_ui_utils.py` - Tests for progress bar completion (new file)

#### **Benefits**

- ✅ **Clear Status**: Users can see which files succeeded/failed
- ✅ **Error Visibility**: Failed files show red error indicators
- ✅ **Clean Interface**: Progress bars are properly completed or marked as failed
- ✅ **Better UX**: No more confusing incomplete progress bars
- ✅ **Debugging**: Error messages are visible on the progress line

#### **Priority**: **High** - This is a user experience issue that affects the perceived reliability of the application

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

### **7. When to Apply SOA + DDD**

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

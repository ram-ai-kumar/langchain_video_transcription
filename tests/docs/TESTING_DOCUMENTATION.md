# Testing Infrastructure Documentation

## Test Organization

The test suite is organized to mirror the source code structure for maintainability and clarity:

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── cli/             # CLI functionality tests
│   ├── core/             # Core configuration and pipeline tests
│   │   ├── test_config.py
│   │   ├── test_negative.py
│   │   └── test_exceptions.py
│   ├── processors/        # Processor tests
│   │   ├── test_audio_processor.py
│   │   └── test_image_processor.py
│   └── utils/             # Utility function tests
│       ├── test_file_utils.py
│       ├── test_media_utils.py
│       └── test_ui_utils.py
├── integration/             # Integration tests for workflows
│   ├── test_pipeline.py
│   ├── test_smoke.py
│   └── test_zta.py
└── conftest.py            # Shared test fixtures and utilities
```

## Test Categories and Markers

### Unit Tests (`@pytest.mark.unit`)
- **Processor Tests** (`@pytest.mark.processor`)
  - Audio processor functionality and Whisper integration
  - Image processor functionality and OCR integration
- **CLI Tests** (`@pytest.mark.cli`)
  - Argument parsing and configuration
  - Help system and error handling
- **Configuration Tests** (`@pytest.mark.config`)
  - PipelineConfig validation and default values
  - File path handling and type validation
- **Utility Tests** (`@pytest.mark.utils`)
  - File discovery and media type detection
  - Path manipulation and sanitization
- **UI Tests** (`@pytest.mark.ui`)
  - Progress reporting and status display
  - Color formatting and user feedback

### Integration Tests (`@pytest.mark.integration`)
- **Smoke Tests** (`@pytest.mark.smoke`)
  - Critical path validation
  - Basic functionality verification
  - CLI help and version display
- **ZTA Tests** (`@pytest.mark.zta`, `@pytest.mark.reliability`)
  - Zero Tolerance Architecture patterns
  - Graceful degradation handling
  - Circuit breaker functionality
  - Retry mechanisms with exponential backoff
  - Bulkhead pattern for large datasets
  - Timeout handling with graceful shutdown
  - Memory leak prevention
  - Idempotency for safe retries
  - Health check escalation

### Specialized Tests
- **Security Tests** (`@pytest.mark.security`)
  - Input validation and sanitization
  - Directory traversal prevention
  - File type validation
  - Path traversal attack prevention
  - Command injection prevention
- **Negative Tests** (`@pytest.mark.negative`)
  - Edge cases and error conditions
  - Empty input handling
  - Invalid type handling
  - Resource exhaustion scenarios
  - Concurrent access simulation
- **Exception Tests** (`@pytest.mark.exception`)
  - Custom exception attributes
  - Error propagation and handling
  - Import error scenarios
  - Resource cleanup on failure

## Running Tests by Category

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Categories
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Smoke tests only
pytest tests/integration/test_smoke.py -v

# Security tests only
pytest tests/unit/security/ -v

# Negative tests only
pytest tests/unit/core/test_negative.py -v

# ZTA tests only
pytest tests/integration/test_zta.py -v

# Processor tests only
pytest tests/unit/processors/ -v

# Slow tests (marked with @pytest.mark.slow)
pytest tests/ -m "slow" -v
```

### Run Tests for CI/CD
```bash
# Fast unit tests for CI
pytest tests/unit/ -x -v --tb=short

# Full test suite with coverage
pytest tests/ --cov=src --cov-report=xml --cov-report=html

# Security-focused tests
pytest tests/unit/security/ -v -k "security"

# Reliability tests
pytest tests/ -k "zta or reliability" -v
```

## Test Coverage Areas

### Functional Coverage
- ✅ Audio processing with Whisper model loading
- ✅ Image processing with OCR functionality
- ✅ CLI argument parsing and validation
- ✅ Configuration management and validation
- ✅ File discovery and media type detection
- ✅ Progress reporting and status display
- ✅ Pipeline orchestration and workflow

### Quality Attributes
- ✅ **Smoke Tests**: Verify critical functionality works
- ✅ **Negative Tests**: Cover edge cases and error conditions
- ✅ **Security Tests**: Prevent common attack vectors
- ✅ **Exception Tests**: Verify proper error handling
- ✅ **ZTA Tests**: Ensure system reliability and resilience

### CI/CD Compatibility
- ✅ **Multiple Python Versions**: Tests run on Python 3.8-3.12
- ✅ **Coverage Reporting**: XML and HTML reports generated
- ✅ **Parallel Execution**: Tests can run concurrently
- ✅ **Marker-Based Selection**: Tests can be run by category
- ✅ **Fast Feedback**: Short test execution for quick CI loops

## Development Workflow

### 1. Write Tests
- Create test files in appropriate directories
- Use descriptive test names and docstrings
- Add proper pytest markers for categorization
- Include both positive and negative test cases

### 2. Run Tests Locally
```bash
# Run specific test file
pytest tests/unit/processors/test_audio_processor.py::TestAudioProcessor::test_init -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=html
```

### 3. Run Tests in CI/CD
- Tests automatically executed via GitHub Actions
- Results uploaded to Codecov for coverage tracking
- Failed tests block pull requests until fixed

## Best Practices

### Test Organization
- **Mirror Source Structure**: Test directories mirror source code organization
- **Descriptive Naming**: Test files clearly indicate what they test
- **Proper Markers**: Use pytest markers for categorization and selection
- **Comprehensive Fixtures**: Shared fixtures reduce code duplication

### Test Design
- **Arrange-Act-Assert**: Clear test structure with setup, action, verification
- **Mocking Strategy**: Mock external dependencies for isolated testing
- **Edge Cases**: Test boundary conditions and error scenarios
- **Idempotency**: Verify operations can be safely retried

### CI/CD Optimization
- **Fast Feedback**: Configure pytest for quick CI execution
- **Parallel Testing**: Use pytest-x for parallel test execution
- **Coverage Gates**: Set minimum coverage thresholds
- **Marker Selection**: Run specific test categories in different CI stages

This comprehensive testing infrastructure ensures code reliability, enables safe refactoring, and provides a solid foundation for continuous integration and deployment.

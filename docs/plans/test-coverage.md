# Comprehensive Test Coverage Plan

This plan outlines a strategy to achieve comprehensive test coverage across smoke, negative, edge, exception, regression, and security test types for the video transcription codebase.

## Current State Analysis

### Existing Test Infrastructure

- **Test files:** 25 (4 integration, 21 unit)
- **Total test functions:** ~142
- **Active tests:** ~48 (34%)
- **Skipped tests:** ~94 (66%)
- **Coverage threshold:** 60% (configured but not measured)
- **Coverage data:** None generated

### Untested Modules (8 files)

- `src/utils/error_logger.py`
- `src/utils/error_summarizer.py`
- `src/utils/performance_optimizer.py`
- `src/utils/whisper_utils.py`
- `src/processors/enhanced_audio_processor.py`
- `src/processors/text_processor.py`
- `src/processors/llm_processor.py`
- `src/generators/study_generator.py` (minimal coverage)

### Test Categories Present

- ✅ Smoke tests (1 file, 4 tests, 2 active)
- ✅ Negative tests (1 file, 10 tests, 2 active)
- ✅ Security tests (5 files, ~35 tests, ~5 active)
- ✅ Exception tests (1 file, 9 tests, 3 active)
- ❌ Edge case tests (no dedicated marker)
- ❌ Regression tests (no dedicated marker)

## Coverage Goals

### Target Metrics

- **Overall code coverage:** 85% (minimum), 90% (target)
- **Critical path coverage:** 95%
- **Security-sensitive code:** 100%
- **Active test rate:** 90% (reduce skip rate from 66% to 10%)
- **Branch coverage:** 80%

### Coverage by Module Type

- **Core modules (config, pipeline, exceptions):** 90%
- **Processors (audio, image, text, LLM):** 85%
- **Generators (PDF, study):** 90%
- **Utilities (file, media, progress):** 80%
- **CLI:** 85%

## Step-by-Step Implementation Priority

**Execute in this order from top to bottom:**

### Priority 1: Setup Coverage Infrastructure (Day 1)

**Why:** Foundation for all coverage work - enables measurement and tracking

- Install coverage tools: `pip install pytest-cov coverage[toml]`
- Update `pyproject.toml` with coverage configuration
- Configure branch coverage and exclusion rules
- Set initial coverage threshold to 60% (current config)
- Generate baseline coverage report

### Priority 2: Regression Tests (Day 2-3)

**Why:** Prevent recurrence of recently fixed bugs - highest business value

- Create `tests/integration/test_regression.py`
- Test Greek character PDF rendering (φ, θ, π) - **critical for recent fix**
- Test Unicode whitespace in paths
- Test code block LaTeX errors
- Test file discovery Unicode handling
- Add version-specific regression markers
- **Target:** 10 tests, 100% active

### Priority 3: Smoke Tests (Day 3-4)

**Why:** Verify critical functionality works - quick wins, builds confidence

- Enable 2 skipped tests in `tests/integration/test_smoke.py`
- Add CLI help/version display test
- Add pipeline initialization test
- Add prerequisite validation test
- Add basic audio processing test
- Add basic PDF generation test
- **Target:** 10 tests, 100% active

### Priority 4: Critical Path Coverage (Day 4-6)

**Why:** Core functionality that everything depends on

- `src/core/pipeline.py` - Main orchestration (target: 95%)
- `src/core/config.py` - Configuration validation (target: 90%)
- `src/processors/audio_processor.py` - Whisper integration (target: 85%)
- `src/generators/pdf_generator.py` - PDF generation (target: 95%)
- Enable 5 skipped tests in `tests/unit/processors/test_audio_processor.py`
- Enable 6 skipped tests in `tests/unit/core/test_config.py`

### Priority 5: Security Tests (Day 6-9)

**Why:** Highest risk - security vulnerabilities can be catastrophic

- Enable 30 skipped security tests across 5 files
- Add input validation tests
- Add path traversal tests
- Add command injection tests
- Add resource limit tests
- Add data sanitization tests
- Add logging security tests (no sensitive data)
- **Target:** 40 tests, 100% active

### Priority 6: Exception Tests (Day 9-11)

**Why:** Proper error handling prevents silent failures

- Enable 6 skipped tests in `tests/unit/core/test_exceptions.py`
- Add tests for custom exception attributes
- Test exception propagation
- Test error message formatting
- Test recovery scenarios
- Add import error handling tests
- Add file permission error tests
- **Target:** 15 tests, 100% active

### Priority 7: Negative Tests (Day 11-13)

**Why:** Test error conditions and invalid inputs

- Enable 8 skipped tests in `tests/unit/core/test_negative.py`
- Add empty/None file path tests
- Add invalid configuration type tests
- Add non-existent directory tests
- Add malformed data tests
- Add permission denied tests
- Add network failure tests
- **Target:** 20 tests, 100% active

### Priority 8: Edge Case Tests (Day 13-15)

**Why:** Boundary conditions often hide bugs

- Create `tests/unit/core/test_edge_cases.py`
- Test zero-byte files
- Test very large files (>1GB)
- Test maximum path lengths
- Test Unicode edge cases (BOM, combining chars)
- Test concurrent access
- Test resource exhaustion
- **Target:** 15 tests, 100% active

### Priority 9: Untested Modules (Day 15-20)

**Why:** Complete coverage across all modules

**High Priority:**

- `tests/unit/generators/test_study_generator.py` (target: 90%)
- `tests/unit/processors/test_text_processor.py` (target: 80%)
- `tests/unit/processors/test_llm_processor.py` (target: 80%)
- `tests/unit/utils/test_whisper_utils.py` (target: 80%)

**Medium Priority:**

- `tests/unit/processors/test_enhanced_audio_processor.py` (target: 80%)
- `tests/unit/utils/test_error_logger.py` (target: 80%)
- `tests/unit/utils/test_error_summarizer.py` (target: 80%)
- `tests/unit/utils/test_performance_optimizer.py` (target: 80%)

### Priority 10: Integration Tests (Day 20-22)

**Why:** End-to-end workflow validation

- Enable 7 skipped tests in `tests/integration/test_pipeline.py`
- Add end-to-end workflow tests
- Add multi-file processing tests
- Add error recovery integration tests
- Add cleanup integration tests
- Enable 6 skipped tests in `tests/integration/test_zta.py`

### Priority 11: Strengthen Existing Tests (Day 22-25)

**Why:** Improve coverage of already-tested modules

- `tests/unit/processors/test_pdf_sanitization.py` - Add Greek character tests
- `tests/unit/utils/test_file_utils.py` - Enable 7 skipped tests
- `tests/unit/utils/test_media_utils.py` - Enable 10 skipped tests
- `tests/unit/utils/test_file_operations_security.py` - Enable 9 skipped tests
- `tests/unit/cli/test_cli.py` - Enable 3 skipped tests
- `tests/unit/cli/test_cli_compliance.py` - Enable 2 skipped tests

### Priority 12: CI/CD Integration (Day 25-26)

**Why:** Automate coverage enforcement

- Add coverage check to `.github/workflows/ci.yml`
- Configure coverage upload to Codecov
- Set coverage threshold to 85%
- Add pre-commit hooks for pytest
- Generate coverage badge

---

## Detailed Implementation Phases

### Phase 1: Foundation & Critical Paths (Week 1-2)

**Goal:** Enable existing tests and cover critical paths

#### 1.1 Setup Coverage Infrastructure (Priority 1)

```bash
# Install coverage tools
pip install pytest-cov coverage[toml]

# Configure coverage in pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/test_*", "*/conftest.py"]
branch = true

[tool.coverage.report]
fail_under = 85
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
```

#### 1.2 Regression Tests (Priority 2)

Create `tests/integration/test_regression.py`:

- Test for previously fixed bugs (Greek character PDF issue)
- Test for file path Unicode issues
- Test for code block LaTeX errors
- Version-specific regression markers
- Data-driven regression tests

#### 1.3 Smoke Tests (Priority 3)

Enhance `tests/integration/test_smoke.py`:

- Enable all 2 skipped tests
- Add CLI smoke tests
- Add pipeline initialization smoke tests
- Add dependency check smoke tests
- Add basic processing smoke tests

#### 1.4 Cover Critical Paths (Priority 4)

- `src/core/pipeline.py` - Main orchestration
- `src/core/config.py` - Configuration validation
- `src/processors/audio_processor.py` - Whisper integration
- `src/generators/pdf_generator.py` - PDF generation (recently fixed)

### Phase 2: Security & Exception Handling (Week 3-4)

**Goal:** Comprehensive security and error handling coverage

#### 2.1 Security Tests (Priority 5)

Enhance security test files:

- Enable all 30 skipped security tests
- Add input validation tests
- Add path traversal tests
- Add command injection tests
- Add resource limit tests
- Add data sanitization tests

#### 2.2 Exception Tests (Priority 6)

Enhance `tests/unit/core/test_exceptions.py`:

- Enable all 6 skipped tests
- Add tests for custom exceptions
- Test exception propagation
- Test error message formatting
- Test recovery scenarios

### Phase 3: Negative & Edge Cases (Week 5-6)

**Goal:** Comprehensive error condition and boundary testing

#### 3.1 Negative Tests (Priority 7)

Enhance `tests/unit/core/test_negative.py`:

- Enable all 8 skipped tests
- Add invalid input tests
- Add malformed data tests
- Add permission denied tests
- Add network failure tests

#### 3.2 Edge Case Tests (Priority 8)

Create `tests/unit/core/test_edge_cases.py`:

- Boundary conditions (empty files, max file sizes)
- Unicode edge cases (BOM, combining characters)
- Path edge cases (max length, special characters)
- Concurrent access edge cases
- Resource exhaustion edge cases

### Phase 4: Module Coverage (Week 7-8)

**Goal:** Achieve 85% coverage across all modules

#### 4.1 Untested Modules (Priority 9)

Create test files for:

- `tests/unit/utils/test_error_logger.py`
- `tests/unit/utils/test_error_summarizer.py`
- `tests/unit/utils/test_performance_optimizer.py`
- `tests/unit/utils/test_whisper_utils.py`
- `tests/unit/processors/test_enhanced_audio_processor.py`
- `tests/unit/processors/test_text_processor.py`
- `tests/unit/processors/test_llm_processor.py`
- `tests/unit/generators/test_study_generator.py`

#### 4.2 Strengthen Existing Tests (Priority 11)

- `tests/unit/processors/test_pdf_sanitization.py` - Add Greek character tests
- `tests/unit/core/test_config.py` - Enable skipped tests
- `tests/unit/utils/test_file_utils.py` - Enable skipped tests

### Phase 5: Integration & CI/CD (Week 8-9)

**Goal:** End-to-end validation and automation

#### 5.1 Integration Tests (Priority 10)

Enhance `tests/integration/test_pipeline.py`:

- Enable all 7 skipped tests
- Add end-to-end workflow tests
- Add multi-file processing tests
- Add error recovery integration tests
- Add cleanup integration tests

#### 5.2 CI/CD Integration (Priority 12)

Add to `.github/workflows/ci.yml`:

```yaml
- name: Run tests with coverage
  run: |
    pytest --cov=src --cov-report=xml --cov-report=term --cov-fail-under=85

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
    fail_ci_if_error: true
```

## Test Type Coverage Strategy

### Smoke Tests

**Purpose:** Verify critical functionality works
**Scope:**

- CLI help/version display
- Pipeline initialization
- Prerequisite validation
- Basic audio processing
- Basic PDF generation
  **Target:** 10 tests, 100% active

### Negative Tests

**Purpose:** Test error conditions and invalid inputs
**Scope:**

- Empty/None file paths
- Invalid configuration types
- Non-existent directories
- Malformed input data
- Permission errors
  **Target:** 20 tests, 100% active

### Edge Case Tests

**Purpose:** Test boundary conditions and unusual scenarios
**Scope:**

- Zero-byte files
- Very large files (>1GB)
- Maximum path lengths
- Unicode edge cases (BOM, combining chars)
- Concurrent access
- Resource exhaustion
  **Target:** 15 tests, 100% active

### Exception Tests

**Purpose:** Verify proper exception handling
**Scope:**

- Custom exception attributes
- Import error handling
- File permission errors
- Disk space errors
- Network timeouts
- Memory exhaustion
  **Target:** 15 tests, 100% active

### Regression Tests

**Purpose:** Prevent recurrence of fixed bugs
**Scope:**

- Greek character PDF rendering (φ, θ, π)
- Unicode whitespace in paths
- Code block LaTeX errors
- File discovery Unicode handling
- Previous security vulnerabilities
  **Target:** 10 tests, 100% active

### Security Tests

**Purpose:** Validate security measures
**Scope:**

- Command injection prevention
- Path traversal prevention
- Input sanitization
- Resource limit enforcement
- File permission validation
- Environment variable injection
- Subprocess command validation
- Logging security (no sensitive data)
  **Target:** 40 tests, 100% active

## Module-by-Module Coverage Plan

### Core Module (`src/core/`)

| File            | Current | Target | Priority |
| --------------- | ------- | ------ | -------- |
| `config.py`     | 40%     | 90%    | High     |
| `pipeline.py`   | 30%     | 95%    | High     |
| `exceptions.py` | 50%     | 90%    | Medium   |

### Processors (`src/processors/`)

| File                          | Current | Target | Priority |
| ----------------------------- | ------- | ------ | -------- |
| `audio_processor.py`          | 20%     | 85%    | High     |
| `image_processor.py`          | 20%     | 85%    | Medium   |
| `text_processor.py`           | 0%      | 80%    | Medium   |
| `llm_processor.py`            | 0%      | 80%    | Medium   |
| `enhanced_audio_processor.py` | 0%      | 80%    | Low      |
| `base.py`                     | 10%     | 85%    | Medium   |

### Generators (`src/generators/`)

| File                 | Current | Target | Priority |
| -------------------- | ------- | ------ | -------- |
| `pdf_generator.py`   | 40%     | 95%    | High     |
| `study_generator.py` | 5%      | 90%    | High     |

### Utilities (`src/utils/`)

| File                       | Current | Target | Priority |
| -------------------------- | ------- | ------ | -------- |
| `file_utils.py`            | 30%     | 85%    | High     |
| `media_utils.py`           | 40%     | 80%    | Medium   |
| `progress_tracker.py`      | 60%     | 85%    | Medium   |
| `subprocess_utils.py`      | 20%     | 85%    | High     |
| `whisper_utils.py`         | 0%      | 80%    | Medium   |
| `error_logger.py`          | 0%      | 80%    | Low      |
| `error_summarizer.py`      | 0%      | 80%    | Low      |
| `performance_optimizer.py` | 0%      | 80%    | Low      |
| `ui_utils.py`              | 70%     | 85%    | Low      |

### CLI (`src/cli/`)

| File      | Current | Target | Priority |
| --------- | ------- | ------ | -------- |
| `main.py` | 30%     | 85%    | Medium   |

## Tooling and CI Integration

### Coverage Reporting

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term --cov-report=xml

# Generate coverage badge
coverage-badge -o docs/coverage.svg
```

### CI/CD Integration

Add to `.github/workflows/ci.yml`:

```yaml
- name: Run tests with coverage
  run: |
    pytest --cov=src --cov-report=xml --cov-report=term --cov-fail-under=85

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
    fail_ci_if_error: true
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: pytest-check
      name: pytest-check
      entry: pytest
      language: system
      pass_filenames: false
      always_run: true
```

### Coverage Enforcement

```toml
# pyproject.toml
[tool.coverage.report]
fail_under = 85
precision = 2
show_missing = true
skip_covered = false
```

## Test Organization

### Directory Structure

```
tests/
├── integration/
│   ├── test_pipeline.py (enable 7 skipped)
│   ├── test_smoke.py (enable 2 skipped)
│   ├── test_zta.py (enable 6 skipped)
│   ├── test_progress_display.py (all active)
│   └── test_regression.py (NEW)
├── unit/
│   ├── core/
│   │   ├── test_config.py (enable 6 skipped)
│   │   ├── test_pipeline_sequential.py (all active)
│   │   ├── test_exceptions.py (enable 6 skipped)
│   │   ├── test_negative.py (enable 8 skipped)
│   │   ├── test_core_security.py (enable 6 skipped)
│   │   └── test_edge_cases.py (NEW)
│   ├── processors/
│   │   ├── test_audio_processor.py (enable 5 skipped)
│   │   ├── test_image_processor.py (enable 6 skipped)
│   │   ├── test_pdf_sanitization.py (all active)
│   │   ├── test_processor_security.py (enable 8 skipped)
│   │   ├── test_study_generator.py (enable 2 skipped)
│   │   ├── test_text_processor.py (NEW)
│   │   ├── test_llm_processor.py (NEW)
│   │   └── test_enhanced_audio_processor.py (NEW)
│   ├── generators/
│   │   ├── test_pdf_generator.py (NEW)
│   │   └── test_study_generator.py (NEW)
│   ├── utils/
│   │   ├── test_file_utils.py (enable 7 skipped)
│   │   ├── test_media_utils.py (enable 10 skipped)
│   │   ├── test_progress_tracker.py (all active)
│   │   ├── test_file_operations_security.py (enable 9 skipped)
│   │   ├── test_file_discovery_duplication.py (all active)
│   │   ├── test_error_logger.py (NEW)
│   │   ├── test_error_summarizer.py (NEW)
│   │   ├── test_whisper_utils.py (NEW)
│   │   └── test_performance_optimizer.py (NEW)
│   ├── security/
│   │   └── test_input_validation.py (all active)
│   └── cli/
│       ├── test_cli.py (enable 3 skipped)
│       └── test_cli_compliance.py (enable 2 skipped)
└── conftest.py (enhance fixtures)
```

### Test Markers

```python
# Existing markers
@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.smoke
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.exception
@pytest.mark.zta

# New markers to add
@pytest.mark.edge
@pytest.mark.regression
@pytest.mark.slow
```

## Fixtures Enhancement

### Add to `conftest.py`

````python
@pytest.fixture
def sample_markdown_with_greek(temp_dir):
    """Create markdown with Greek characters for regression testing."""
    md_path = temp_dir / "greek_test.md"
    md_path.write_text("Mathematical symbols: φ (phi), θ (theta), π (pi)")
    return md_path

@pytest.fixture
def sample_markdown_with_code_blocks(temp_dir):
    """Create markdown with code blocks for LaTeX testing."""
    md_path = temp_dir / "code_test.md"
    md_path.write_text("```python\ndef hello():\n    print('world')\n```")
    return md_path

@pytest.fixture
def large_file(temp_dir):
    """Create a large file for edge case testing."""
    large_path = temp_dir / "large.txt"
    large_path.write_bytes(b"x" * (10 * 1024 * 1024))  # 10MB
    return large_path

@pytest.fixture
def unicode_path(temp_dir):
    """Create path with Unicode characters for edge case testing."""
    unicode_dir = temp_dir / "测试文件"
    unicode_dir.mkdir()
    return unicode_dir
````

## Metrics and Reporting

### Weekly Metrics to Track

1. Overall coverage percentage
2. Active test percentage (reduce skip rate)
3. Number of tests per category
4. Branch coverage
5. Module coverage breakdown

### Success Criteria

- [ ] Coverage >= 85% overall
- [ ] Active tests >= 90%
- [ ] All critical paths >= 95% coverage
- [ ] All security tests active
- [ ] All regression tests for known bugs
- [ ] CI coverage checks passing
- [ ] Coverage report generated on each PR

## Risk Mitigation

### Potential Risks

1. **High skip rate** - Tests may be skipped due to missing dependencies
   - Mitigation: Set up test dependencies in requirements-dev.txt
2. **External dependencies** - Whisper, Tesseract, Ollama may not be available
   - Mitigation: Use mocks for external dependencies in unit tests
3. **Flaky tests** - Integration tests may be unstable
   - Mitigation: Use retries, proper cleanup, and isolated environments
4. **Slow test execution** - Full suite may take too long
   - Mitigation: Use pytest-xdist for parallel execution, mark slow tests

### Dependencies

```txt
# requirements-dev.txt
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-xdist>=3.0.0
pytest-mock>=3.10.0
coverage[toml]>=7.0.0
```

## Timeline Summary

| Phase   | Duration | Deliverables                                                  |
| ------- | -------- | ------------------------------------------------------------- |
| Phase 1 | Week 1-2 | Enable skipped tests, setup coverage, cover critical paths    |
| Phase 2 | Week 3-5 | Create tests for untested modules, strengthen existing tests  |
| Phase 3 | Week 6-7 | Edge, regression, exception, negative, security test coverage |
| Phase 4 | Week 8   | Smoke and integration test enhancement                        |
| Total   | 8 weeks  | 85%+ coverage, comprehensive test suite                       |

## Next Steps

1. Review and approve this plan
2. Set up coverage infrastructure (Phase 1.2)
3. Begin enabling skipped tests (Phase 1.1)
4. Create test files for untested modules (Phase 2.1)
5. Implement specialized test types (Phase 3)
6. Integrate with CI/CD pipeline
7. Monitor coverage metrics weekly

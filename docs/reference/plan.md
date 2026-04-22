# Refactor Plan: Remove UI Code, Switch to Sequential Processing

**Goal**: Replace the concurrent sliding-window scheduler and all polished UI code (Rich
progress bars, tree visualization, progress simulators, resource manager) with simple
sequential one-by-one file processing, while keeping all pipeline functionality intact.

---

## 1. Scope Summary

### What is being removed

| Item                                                                                                                | Location                           | Reason                             |
| ------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ---------------------------------- |
| Rich `Progress`/spinner/bar                                                                                         | `src/utils/ui_utils.py`            | UI-specific                        |
| `ProgressReporter` class                                                                                            | `src/utils/ui_utils.py`            | UI-specific                        |
| `PROCESSING_STEPS` dict                                                                                             | `src/utils/ui_utils.py`            | Only used by ProgressReporter      |
| `ProgressSimulator` + helpers                                                                                       | `src/utils/simple_progress.py`     | UI-specific progress thread        |
| `ProgressParser`, `ProgressInfo`, `ProgressCallback`, `run_command_with_progress`, etc.                             | `src/utils/progress_subprocess.py` | UI progress capture only           |
| `ProgressType` enum                                                                                                 | `src/utils/progress_subprocess.py` | Only used for UI progress          |
| `RealtimeProgress`, `RealtimeProgressManager`, `ProgressTracker`, `WhisperProgressTracker`, `FFmpegProgressTracker` | `src/utils/realtime_progress.py`   | UI-specific                        |
| `ResourceManager`                                                                                                   | `src/utils/resource_manager.py`    | Only used to calibrate concurrency |
| Sliding window scheduler (`concurrent.futures`, `threading.Semaphore`, window logic)                                | `src/core/pipeline.py`             | Concurrent UI-driven design        |
| Directory tree print with emojis                                                                                    | `src/core/pipeline.py`             | UI-specific                        |
| `progress_reporter.start_processing / next_step / update_task_progress / complete_processing / stop` calls          | `src/core/pipeline.py`             | UI-specific                        |
| Progress simulation calls in `process_single_source`                                                                | `src/core/pipeline.py`             | UI-specific                        |
| `--max-workers`, `--no-batch`, `--batch-size`, `--no-optimizations` CLI args                                        | `src/cli/main.py`                  | No longer applicable               |
| `concurrency`, `window_size`, `heavy_task_semaphore`, `resources` pipeline attrs                                    | `src/core/pipeline.py`             | Concurrency scaffolding            |

### What is being kept

| Item                                                                                 | Location                        | Reason                                                                              |
| ------------------------------------------------------------------------------------ | ------------------------------- | ----------------------------------------------------------------------------------- |
| `StatusReporter` class                                                               | `src/utils/ui_utils.py`         | Functional CLI feedback (info/warn/error/success)                                   |
| `ColorFormatter` class                                                               | `src/utils/ui_utils.py`         | Used throughout CLI for coloured output                                             |
| `run_silent_command`, `capture_command_output`, `setup_global_silence`               | `src/utils/subprocess_utils.py` | Core subprocess helpers                                                             |
| `FileDiscovery`, `FileManager`                                                       | `src/utils/file_utils.py`       | Unchanged                                                                           |
| `process_single_source`                                                              | `src/core/pipeline.py`          | Core pipeline logic                                                                 |
| `_process_media_groups`, `_process_image_groups`, `_process_loose_images`            | `src/core/pipeline.py`          | Sequential processing helpers (already exist — just remove progress reporter calls) |
| `_migrate_legacy_unsanitized_files`                                                  | `src/core/pipeline.py`          | Data-migration utility                                                              |
| `StudyMaterialGenerator`, `PDFGenerator`                                             | `src/generators/`               | Unchanged                                                                           |
| All processors (`AudioProcessor`, `ImageProcessor`, `TextProcessor`, `LLMProcessor`) | `src/processors/`               | Unchanged                                                                           |
| All existing tests not listed for deletion                                           | `tests/`                        | Unchanged                                                                           |

---

## 2. File-by-File Changes

### 2.1 `src/utils/ui_utils.py` — Simplify

**Remove**:

- `PROCESSING_STEPS` dict
- All `rich` imports (`Progress`, `SpinnerColumn`, `TextColumn`, `BarColumn`, `TaskProgressColumn`, `TimeElapsedColumn`)
- `ProgressReporter` class (all methods: `start_processing`, `next_step`, `update_task_progress`, `update_task_progress_legacy`, `complete_processing`, `stop`, `get_progress_string`, `format_pipeline_steps`)
- Import of `ProgressType` from `progress_subprocess`

**Keep**:

- `ColorFormatter` class (unchanged)
- `StatusReporter` class (unchanged)
- All existing imports needed by the two kept classes (`logging`, `sys`, `time`, `threading`, `typing`)

**Result**: `ui_utils.py` becomes ~60 lines (down from ~231). No Rich dependency.

---

### 2.2 `src/utils/simple_progress.py` — Delete

Entire file can be deleted. It only contains `ProgressSimulator`, `simulate_transcription_progress`, and `simulate_extraction_progress`, all of which are UI-only.

---

### 2.3 `src/utils/progress_subprocess.py` — Delete or Gut

The file serves two purposes:

1. **UI progress capture** (`ProgressType`, `ProgressInfo`, `ProgressParser`, `ProgressCallback`, `run_command_with_progress`, `ffmpeg_with_progress`, `whisper_with_progress`, `temporary_progress_env`) — all UI-specific, remove.
2. **Nothing else** — the subprocess running helpers that matter live in `subprocess_utils.py`.

**Action**: Delete the file entirely. No other production code imports from it after the other changes (it is imported by `ui_utils.py` only for `ProgressType`, which will also be removed).

---

### 2.4 `src/utils/realtime_progress.py` — Delete

Entire file can be deleted. Contains `ProgressStage`, `RealtimeProgress`, `RealtimeProgressManager`, `ProgressTracker`, `WhisperProgressTracker`, `FFmpegProgressTracker`, and factory helpers. All UI-specific. Nothing else imports it.

---

### 2.5 `src/utils/resource_manager.py` — Delete

`ResourceManager` was introduced solely to auto-detect RAM and recommend concurrency
(`max_heavy_tasks`, `max_total_tasks`, `window_size`). With sequential processing, no
concurrency calibration is needed. Delete the file.

---

### 2.6 `src/core/pipeline.py` — Major refactor

**Remove entirely**:

- `import concurrent.futures`
- `import itertools`
- `import threading`
- `PIPELINE_WINDOW_SIZE` and `PIPELINE_CONCURRENCY` module-level constants
- Import of `ProgressReporter`, `PROCESSING_STEPS` from `ui_utils`
- Import of `ResourceManager` from `resource_manager`

**In `__init__`**:

- Remove `self.status_reporter = StatusReporter(...)` → keep
- Remove `self.progress_reporter = ProgressReporter(...)` → remove
- Remove `self.resource_manager = ResourceManager(...)`
- Remove `self.resources = self.resource_manager.get_concurrency_recommendation()`
- Remove `self.concurrency`, `self.window_size`, `self.heavy_task_semaphore`
- Keep everything else unchanged

**In `_load_whisper_model`**:

- Replace `self.status_reporter.info(...)` calls with `logging.info(...)` or keep `status_reporter.info(...)` — keep `status_reporter` since it's still present

**In `process_directory`**:

- Remove the tree-building logic (`tree`, `add_task`, `traverse_tree`)
- Remove the sliding window executor block (`concurrent.futures.ThreadPoolExecutor`, `window`, `itertools.islice`, `threading.Lock`, `processed_count`, `error_count` list wrappers)
- Remove `execute_task` inner function and all progress reporter calls within it
- Remove the `print(f"\n📁 {directory.name}/")` emoji output
- Replace with three sequential calls to the existing private helpers:
  1. `self._process_media_groups(file_groups, directory)`
  2. `self._process_image_groups(file_groups, directory)`
  3. `self._process_loose_images(directory)`
- These helpers already exist and already do the correct sequential processing.
  They just need their `progress_reporter.*` calls removed (see below).
- Accumulate counts from the three helpers and return a `ProcessResult` as now.

**In `_process_media_groups`** (lines 420–457):

- Remove `steps = PROCESSING_STEPS.get(...)` line
- Remove `self.progress_reporter.start_processing(...)` call
- Remove `self.progress_reporter.complete_processing(...)` calls
- Keep all file processing logic, result checks, stem tracking, error logging

**In `_process_image_groups`** (lines 459–513):

- Same as above — remove all `progress_reporter.*` calls and `PROCESSING_STEPS` references
- Keep all image processing, transcript generation, study material generation logic

**In `_process_loose_images`** (lines 515–575):

- Same — remove all `progress_reporter.*` calls
- Keep all loose image grouping and processing logic

**In `process_single_source`** (lines 610–766):

- Remove `from src.utils.simple_progress import simulate_extraction_progress` (lazy import)
- Remove `progress_simulator = simulate_extraction_progress(...)` block for audio extraction
- Remove `progress_simulator.start(...)` and `progress_simulator.stop(...)` calls
- Remove `from src.utils.simple_progress import simulate_transcription_progress` (lazy import)
- Remove `progress_simulator = simulate_transcription_progress(...)` block for transcription
- Remove `import librosa` block for audio duration (only needed for progress estimation)
- Remove all `self.progress_reporter.next_step(...)` calls
- Keep all actual processing calls (`audio_processor.extract_audio_from_video`, `audio_processor.process`, `text_processor.process`, `study_generator.generate`, `study_generator.generate_pdf_only`)
- Keep all `ProcessResult` returns and early exits for `config.target`

**In `process_directory` — `KeyboardInterrupt` handler**:

- Remove `self.progress_reporter.stop()` call
- Remove Rich markup from the print statement (`[bold red]...[/bold red]`)
- Replace with a plain `print()` message

**Logging in `process_directory`**:

- Replace bare `print(...)` calls that were tree display with structured `self.status_reporter.info(...)` or `logging.info(...)` calls so the pipeline still gives feedback in verbose mode.

**`get_pipeline_info`** — no changes needed.

---

### 2.7 `src/cli/main.py` — Remove dead CLI args

**Remove from `create_parser`**:

- `--no-optimizations` / `--no_optimizations` argument
- `--max-workers` argument
- `--no-batch` argument
- `--batch-size` argument

**In `create_config`**:

- Remove `enable_performance_optimizations` key from `config_dict`
- Remove `max_workers` key from `config_dict`
- Remove `use_batch_processing` key from `config_dict`
- Remove `batch_size` key from `config_dict`

**Keep**:

- `--verbose / -v` (still used by `StatusReporter`)
- `--device` (used by audio processor for Whisper device selection if config supports it)
- All other args unchanged

---

### 2.8 `src/core/config.py` — Audit and cleanup

Read the file and remove any fields that are now unused:

- `max_workers: Optional[int]` — remove if only used by the scheduler
- `use_batch_processing: bool` — remove
- `batch_size: int` — remove
- `enable_performance_optimizations: bool` — remove

Keep `device` if it's used by `AudioProcessor` for hardware selection.

---

## 3. Test Suite Changes

### 3.1 Delete — tests for removed components

| File                                             | Reason                                                                                                                                                                           |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/unit/core/test_pipeline_scheduler.py`     | Tests the sliding window scheduler, which is being removed. Constants `PIPELINE_WINDOW_SIZE`/`PIPELINE_CONCURRENCY` will no longer exist.                                        |
| `tests/unit/utils/test_resource_optimization.py` | Tests `ResourceManager` and its integration with pipeline concurrency attributes (`pipeline.concurrency`, `pipeline.window_size`, `pipeline.heavy_task_semaphore`). All removed. |

### 3.2 Update — `tests/unit/test_ui_utils.py`

**Remove** the `TestProgressReporter` class and all its test methods — `ProgressReporter` is being deleted.

**Keep** (unchanged):

- `TestStatusReporter` class and all tests
- `TestColorFormatter` class and all tests

**Update imports**: Remove `ProgressReporter` from the import line.

### 3.3 Update — `tests/unit/core/test_pipeline_scheduler.py` → Replace with sequential test

Rather than deleting with nothing, add a new test file
`tests/unit/core/test_pipeline_sequential.py` that verifies the new sequential behaviour:

- All discovered tasks execute exactly once
- Processing order is deterministic (sorted)
- A failing task does not abort remaining tasks
- Empty directory returns success
- `process_directory` returns correct counts

These tests should mock `process_single_source` exactly as the scheduler tests did but
without threading or timing dependencies.

### 3.4 Keep unchanged

| File                                                  | Status                                                                         |
| ----------------------------------------------------- | ------------------------------------------------------------------------------ |
| `tests/unit/utils/test_file_discovery_duplication.py` | No changes — `FileDiscovery` is unchanged                                      |
| `tests/unit/processors/test_pdf_sanitization.py`      | No changes — `PDFGenerator` and `FileDiscovery.get_output_paths` are unchanged |
| All other existing test files                         | Unchanged                                                                      |

---

## 4. Documentation Changes

### 4.1 `docs/reference/TODO.md`

- Mark item **2. Async / Parallel File Processing** as **Reverted** with a note explaining the switch back to sequential processing for simplicity.
- Remove or update the `PIPELINE_WINDOW_SIZE` and `PIPELINE_CONCURRENCY` references.

### 4.2 `docs/architecture/PROCESSING_ARCHITECTURE.md`

- Update pipeline description: replace "sliding window concurrent scheduler" language with "sequential processing".
- Remove any diagrams or descriptions referencing `ThreadPoolExecutor`, window size, or concurrency limits.

### 4.3 `docs/guides/PERFORMANCE_OPTIMIZATION.md`

- Remove sections referencing `ResourceManager`, `max_workers`, `use_batch_processing`, `batch_size`, and the sliding window scheduler.
- Keep sections about hardware acceleration (Whisper device selection), prompt tuning, and any non-concurrency optimizations.

### 4.4 `docs/architecture/ARCHITECTURE.md`

- Update pipeline section to reflect sequential processing flow.
- Remove references to `ResourceManager` from the component inventory.

### 4.5 `docs/usage/USAGE.md`

- Remove `--max-workers`, `--no-batch`, `--batch-size`, `--no-optimizations` from the CLI reference table/examples.

---

## 5. Dependency Cleanup

After the above changes, verify the following packages are no longer imported anywhere and
can be removed from `requirements.txt` if they were added solely for UI:

- `rich` — imported by `ui_utils.py` for `ProgressReporter`. After removal, check if any other file imports it. If not, remove from requirements.
- `psutil` — imported by `resource_manager.py`. If file is deleted and nothing else uses it, remove from requirements.

---

## 6. Execution Order

Steps should be executed in this order to keep the codebase always importable:

1. **Delete `src/utils/simple_progress.py`**
2. **Delete `src/utils/realtime_progress.py`**
3. **Delete `src/utils/resource_manager.py`**
4. **Simplify `src/utils/ui_utils.py`** (remove ProgressReporter; keep StatusReporter + ColorFormatter)
5. **Delete `src/utils/progress_subprocess.py`**
6. **Refactor `src/core/pipeline.py`** (remove all UI/concurrency code; restore sequential _process_\* flow)
7. **Audit `src/core/config.py`** (remove dead fields)
8. **Update `src/cli/main.py`** (remove dead CLI args)
9. **Delete test files**: `test_pipeline_scheduler.py`, `test_resource_optimization.py`
10. **Update `tests/unit/test_ui_utils.py`** (remove ProgressReporter tests)
11. **Write `tests/unit/core/test_pipeline_sequential.py`** (new sequential tests)
12. **Update documentation** (TODO.md, ARCHITECTURE.md, PROCESSING_ARCHITECTURE.md, PERFORMANCE_OPTIMIZATION.md, USAGE.md)
13. **Run full test suite** and fix any remaining import errors or broken references

---

## 7. Risks and Considerations

| Risk                                                                                                                     | Mitigation                                                                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ProgressType` imported by `ui_utils.py` — removing `progress_subprocess.py` breaks this import                          | Remove the `ProgressType` import from `ui_utils.py` at the same time (step 4 before step 5)                                                                                                      |
| `simple_progress` is imported lazily inside `process_single_source`                                                      | Remove those lazy imports in step 6 before deleting the file in step 1, OR delete file first (ImportError is caught in try/except already) — safest: remove lazy imports first, then delete file |
| `ResourceManager` import in `pipeline.py` and its test — deleting breaks tests                                           | Delete test file first (step 9), then refactor pipeline (step 6)                                                                                                                                 |
| `PIPELINE_WINDOW_SIZE` / `PIPELINE_CONCURRENCY` exported from `pipeline.py` and imported in `test_pipeline_scheduler.py` | Delete test file before refactoring pipeline                                                                                                                                                     |
| `StatusReporter` is kept but `self.status_reporter` is currently initialized in `__init__` — ensure this is preserved    | Explicitly check **init** during pipeline refactor                                                                                                                                               |
| `_process_media_groups`, `_process_image_groups`, `_process_loose_images` currently contain `progress_reporter.*` calls  | These must be cleaned of UI calls (step 6) before they are wired into `process_directory`                                                                                                        |
| Config fields `max_workers`, `use_batch_processing`, `batch_size` may be referenced by existing passing tests            | Audit `tests/unit/core/test_config.py` before removing config fields                                                                                                                             |

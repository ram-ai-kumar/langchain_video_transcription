"""Unit tests for the sliding window task scheduler in VideoTranscriptionPipeline.

The scheduler (inside process_directory) maintains:
  - PIPELINE_WINDOW_SIZE = 4   max tasks loaded (queued + running) at once
  - PIPELINE_CONCURRENCY = 2   max tasks executing simultaneously

As each task completes, the next unseen task is pulled into the window and
submitted to the executor, keeping the pipeline saturated without overloading
memory or the LLM/Whisper models.
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from src.core.pipeline import (
    PIPELINE_CONCURRENCY,
    PIPELINE_WINDOW_SIZE,
    VideoTranscriptionPipeline,
)
from src.processors.base import ProcessResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok():
    """Minimal successful ProcessResult."""
    return ProcessResult(success=True, message="ok")


@pytest.fixture
def pipeline():
    """VideoTranscriptionPipeline with all heavy dependencies mocked out.

    The context managers remain active for the lifetime of each test so that
    any attribute look-ups on the pipeline's components hit Mocks, not the
    real Whisper / Torch / Ollama stack.
    """
    patches = [
        patch("src.core.pipeline.whisper"),
        patch("src.core.pipeline.torch"),
        patch("src.core.pipeline.StudyMaterialGenerator"),
        patch("src.core.pipeline.AudioProcessor"),
        patch("src.core.pipeline.TextProcessor"),
        patch("src.core.pipeline.ImageProcessor"),
        patch("src.core.pipeline.FileDiscovery"),
        patch("src.core.pipeline.MediaProcessorFactory"),
    ]
    started = [p.start() for p in patches]

    config = MagicMock()
    config.target = "pdf"
    config.generate_pdf = True
    config.verbose = False
    config.is_image_file.return_value = False

    pl = VideoTranscriptionPipeline(config)
    pl.progress_reporter = MagicMock()
    pl.status_reporter = MagicMock()

    yield pl

    for p in patches:
        p.stop()


def _wire_txt_tasks(pipeline, tmp_path, n: int) -> dict:
    """Create n .txt stub files and configure file_discovery to return them."""
    files = {}
    for i in range(n):
        stem = f"file{i:02d}"
        txt = tmp_path / f"{stem}.txt"
        txt.touch()
        files[stem] = [txt]

    pipeline.file_discovery.group_files_by_stem.return_value = files
    pipeline.file_discovery.find_primary_source.side_effect = lambda f: (f[0], "text")
    pipeline.file_discovery.separate_image_files.return_value = []
    pipeline.file_discovery.discover_files.return_value = []
    return files


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSchedulerConstants:
    def test_window_size(self):
        assert PIPELINE_WINDOW_SIZE == 4

    def test_concurrency(self):
        assert PIPELINE_CONCURRENCY == 2


# ---------------------------------------------------------------------------
# Core scheduler behaviour
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSlidingWindowScheduler:

    def test_all_tasks_executed_exactly_once(self, pipeline, tmp_path):
        """Every discovered task runs exactly once — no skips, no duplicates."""
        executed = []
        lock = threading.Lock()

        def fake(src, start_type, task_name=None):
            with lock:
                executed.append(src.name)
            return _ok()

        _wire_txt_tasks(pipeline, tmp_path, 8)
        pipeline.process_single_source = fake
        pipeline.process_directory(tmp_path)

        assert len(executed) == 8
        assert len(set(executed)) == 8

    def test_peak_concurrency_never_exceeds_limit(self, pipeline, tmp_path):
        """At most PIPELINE_CONCURRENCY tasks execute simultaneously."""
        lock = threading.Lock()
        active = [0]
        peak = [0]

        def fake(src, start_type, task_name=None):
            with lock:
                active[0] += 1
                if active[0] > peak[0]:
                    peak[0] = active[0]
            time.sleep(0.02)          # hold the slot long enough for overlap
            with lock:
                active[0] -= 1
            return _ok()

        _wire_txt_tasks(pipeline, tmp_path, 6)
        pipeline.process_single_source = fake
        pipeline.process_directory(tmp_path)

        assert peak[0] <= PIPELINE_CONCURRENCY

    def test_empty_task_list_returns_success(self, pipeline, tmp_path):
        """Empty directory exits cleanly with a success result."""
        pipeline.file_discovery.group_files_by_stem.return_value = {}
        pipeline.file_discovery.discover_files.return_value = []

        result = pipeline.process_directory(tmp_path)

        assert result.success is True

    @pytest.mark.parametrize("n", [1, 2, 3])
    def test_fewer_tasks_than_window_size(self, pipeline, tmp_path, n):
        """Works correctly when task count < PIPELINE_WINDOW_SIZE."""
        executed = []

        def fake(src, start_type, task_name=None):
            executed.append(src.name)
            return _ok()

        _wire_txt_tasks(pipeline, tmp_path, n)
        pipeline.process_single_source = fake
        pipeline.processed_stems = set()
        pipeline.process_directory(tmp_path)

        assert len(executed) == n

    def test_exception_in_task_does_not_block_remaining(self, pipeline, tmp_path):
        """A task that raises an exception does not stall the rest of the window."""
        good = []
        lock = threading.Lock()

        def fake(src, start_type, task_name=None):
            if src.stem == "bad":
                raise RuntimeError("Simulated failure")
            with lock:
                good.append(src.name)
            return _ok()

        files = {
            "bad":   [tmp_path / "bad.txt"],
            "good1": [tmp_path / "good1.txt"],
            "good2": [tmp_path / "good2.txt"],
            "good3": [tmp_path / "good3.txt"],
        }
        for fl in files.values():
            fl[0].touch()

        pipeline.file_discovery.group_files_by_stem.return_value = files
        pipeline.file_discovery.find_primary_source.side_effect = lambda f: (f[0], "text")
        pipeline.file_discovery.separate_image_files.return_value = []
        pipeline.file_discovery.discover_files.return_value = []
        pipeline.process_single_source = fake

        pipeline.process_directory(tmp_path)

        assert len(good) == 3

    def test_large_batch_all_complete(self, pipeline, tmp_path):
        """All tasks complete even for batches much larger than the window."""
        executed = []
        lock = threading.Lock()

        def fake(src, start_type, task_name=None):
            with lock:
                executed.append(src.name)
            return _ok()

        _wire_txt_tasks(pipeline, tmp_path, 20)
        pipeline.process_single_source = fake
        pipeline.process_directory(tmp_path)

        assert len(executed) == 20
        assert len(set(executed)) == 20

    def test_window_slides_pulls_next_task_on_completion(self, pipeline, tmp_path):
        """Tasks beyond PIPELINE_WINDOW_SIZE only start after earlier ones complete.

        Strategy:
        - 6 tasks total; tasks 0-1 are held with blocking events.
        - After a short delay the controller releases them one at a time.
        - We verify all 6 tasks eventually start (window slid through them all)
          and that peak concurrency never exceeded 2.
        """
        lock = threading.Lock()
        started = []
        peak = [0]
        active = [0]
        release = [threading.Event() for _ in range(6)]

        def fake(src, start_type, task_name=None):
            idx = int(src.stem[4:])           # "file01" → 1
            with lock:
                active[0] += 1
                if active[0] > peak[0]:
                    peak[0] = active[0]
                started.append(idx)
            release[idx].wait(timeout=5)
            with lock:
                active[0] -= 1
            return _ok()

        _wire_txt_tasks(pipeline, tmp_path, 6)
        pipeline.process_single_source = fake

        def controller():
            time.sleep(0.05)               # let executor seed window & start 0,1
            for i in range(6):
                release[i].set()
                time.sleep(0.03)           # stagger completions so window slides

        t = threading.Thread(target=controller, daemon=True)
        t.start()

        pipeline.process_directory(tmp_path)
        t.join(timeout=10)

        assert len(started) == 6
        assert peak[0] <= PIPELINE_CONCURRENCY

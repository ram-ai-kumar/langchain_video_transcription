# Processing Architecture

[← Back to README](../README.md)

The pipeline is designed as an **intelligent, modular sequence of transformations with a recursive traversal engine**. It automatically scans the entire directory subtree and processes all media types with a **three-pass approach**:

## Three-Pass Processing System

1. **Pass 1**: Video/Audio/Text groups (priority: video > audio > text)

2. **Pass 2**: Image groups (including those sharing stems with other media)

3. **Pass 3**: Loose images (folder-wide processing)

## Smart Conflict Resolution

- **Mixed stems**: `lecture1.mp4` + `lecture1.png` → `lecture1.txt` + `lecture1_images.txt`
- **Image-only stems**: `slides01.png` + `slides01.jpg` → `slides01.txt`
- **Loose images**: `random.gif` → `folder_images.txt`

## PDF Generation Strategy

- **Tectonic**: XeTeX-based engine with native Unicode support and automatic package management
- **Minimal fallback**: Basic PDF generation without custom formatting

Each stage:

- Checks for existing artifacts (skip if already generated).
- Runs independently but feeds into the next stage.
- Updates CLI output in place, showing progress with spinners.
- Produces reusable artifacts (`.txt`, `.md`, `.pdf`) for downstream use.

This orchestration ensures **idempotency, scalability, and clarity** — critical traits for production-ready automation.

## Sliding Window Scheduler

After the three-pass tree traversal collects all tasks, they are dispatched via a **sliding window scheduler** rather than submitting everything to the executor at once:

| Parameter   | Value | Constant               |
| ----------- | ----- | ---------------------- |
| Window size | 4     | `PIPELINE_WINDOW_SIZE` |
| Concurrency | 2     | `PIPELINE_CONCURRENCY` |

**How it works:**

1. Up to 4 tasks are submitted to the executor initially (2 running, 2 queued).
2. Whenever any active task completes, the _next unseen_ task from the iterator is pulled into the window and submitted.
3. The executor cap of 2 threads ensures at most 2 tasks run simultaneously at all times.

```text
t=0    Window: [F1, F2, F3, F4]   Running: F1, F2   Queued: F3, F4
t=Δ    F1 done → start F3, pull F5 into window
       Window: [F2, F3, F4, F5]   Running: F2, F3   Queued: F4, F5
t=2Δ   F3 done → start F4, pull F6 into window
       Window: [F2, F4, F5, F6]   Running: F2, F4   Queued: F5, F6
...
```

**Why not submit everything at once?**

On large directories the old approach (unbounded pool) would submit hundreds of futures simultaneously, loading all task metadata into memory and potentially saturating the LLM or Whisper model before earlier tasks had released their resources. The sliding window keeps memory and I/O pressure bounded regardless of directory size.

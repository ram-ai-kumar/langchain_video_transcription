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

## Sequential Processing

The pipeline now uses **simple sequential processing** for maximum reliability and simplicity. Files are processed one by one in a deterministic order:

**How it works:**

1. Files are discovered and grouped by stem (filename without extension)
2. Groups are processed in alphabetical order for predictable behavior
3. Within each group, processing follows the priority: video > audio > text > images
4. Each file is processed completely before moving to the next

**Benefits of sequential processing:**

- **Simplicity**: No complex concurrency management or race conditions
- **Predictability**: Deterministic processing order makes debugging easier
- **Resource efficiency**: No resource contention between concurrent tasks
- **Reliability**: A failing task doesn't affect other tasks
- **Memory efficiency**: Constant memory usage regardless of directory size

**Error handling:**

- Individual file failures are logged but don't stop processing of remaining files
- The pipeline reports total success/failure counts at the end
- Each processing stage can be interrupted with Ctrl+C while maintaining clean shutdown

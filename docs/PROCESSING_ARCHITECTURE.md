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

- **XeLaTeX**: Native Unicode support for Greek letters and special characters
- **pdfLaTeX**: Enhanced with explicit Unicode character mappings
- **Minimal fallback**: Basic PDF generation without custom formatting

Each stage:

- Checks for existing artifacts (skip if already generated).
- Runs independently but feeds into the next stage.
- Updates CLI output in place, showing progress with spinners.
- Produces reusable artifacts (`.txt`, `.md`, `.pdf`) for downstream use.

This orchestration ensures **idempotency, scalability, and clarity** — critical traits for production-ready automation.

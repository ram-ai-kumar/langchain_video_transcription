# LangChain Video Transcription & Study Material Generator

## Overview

This project began as a simple experiment: transcribing and understanding a few educational videos.  
It quickly evolved into a **fully automated pipeline** that transforms raw video content into **rich learning material** — complete with transcripts, structured summaries, glossaries, and practice questions — all orchestrated seamlessly.

The result is a system that demonstrates not only technical execution but also the **architectural thinking** required to design scalable, reliable, and extensible solutions.

---

## Features

- **Recursive Processing**: Scans the entire directory subtree and processes files in every folder.
- **Deterministic Ordering**: Visits folders, files, and filename groups in **chronological/lexicographic ascending order by name** (case-insensitive) so runs are repeatable and easy to reason about.
- **Multi-Source Entry**: Start from **Video**, **Audio**, or **Text** files.
- **Video → Audio Extraction**: Uses `ffmpeg` to isolate audio streams from video files (skipped if starting from audio).
- **Audio → Transcript**: Employs [OpenAI Whisper](https://github.com/openai/whisper) for accurate speech-to-text transcription (skipped if starting from text).
- **Transcript → Study Chapter**: Leverages [LangChain](https://www.langchain.com/) with Ollama LLM models to generate a **standalone textbook-style chapter** (not just a summary) based on the discovered topics.
- **Rich Study Material Structure**:
  - Learning objectives
  - Executive overview
  - Core concepts and precise definitions
  - In-depth coverage with best practices and pitfalls
  - Glossary of important terms
  - Practice questions (MCQ, short answer, and critical thinking)
- **Image-Only Folders → OCR → Study Pipeline**: If a folder only contains images (e.g., slide decks or scanned pages), the script OCRs them into a single transcript and then feeds that into the same study-material + PDF pipeline.
- **Markdown → PDF**: Converts study material into polished PDFs using Pandoc + LaTeX.
- **CLI Experience**: Clean, readable progress updates with dynamic pipeline paths and spinners.

---

## Tools & Technologies

| Stage                    | Tool/Technology                     | Purpose                              |
| ------------------------ | ----------------------------------- | ------------------------------------ |
| Video → Audio            | **ffmpeg**                          | Reliable audio extraction            |
| Audio → Text             | **Whisper**                         | State-of-the-art transcription       |
| Text → Summary           | **LangChain Core** + **Ollama LLM** | Prompt orchestration & summarization |
| Summary → Study Material | **LangChain PromptTemplate**        | Rich, structured learning content    |
| Markdown → PDF           | **Pandoc** + **LaTeX**              | Professional document generation     |
| CLI UX                   | **Python sys.stdout + spinner**     | User-friendly progress visualization |

---

The pipeline is designed as an **intelligent, modular sequence of transformations with a recursive traversal engine**. It automatically scans the entire directory subtree and detects the best starting point for each filename:

- **Video Entry**: `video > audio > transcript > study material > PDF`
- **Audio Entry**: `audio > transcript > study material > PDF`
- **Text Entry**: `transcript > study material > PDF`

Each stage:

- Checks for existing artifacts (skip if already generated).
- Runs independently but feeds into the next stage.
- Updates CLI output in place, showing progress with spinners.
- Produces reusable artifacts (`.txt`, `.md`, `.pdf`) for downstream use.

This orchestration ensures **idempotency, scalability, and clarity** — critical traits for production-ready automation.

---

## Why This Project Showcases Engineering Excellence

- **Deep Research**: Started with exploring Whisper and LangChain, evolved into a full pipeline.
- **Solution Design**: Identified pain points (manual transcription, scattered notes) and designed a structured workflow.
- **Architecture**: Modular, fault-tolerant, idempotent design with clear separation of concerns.
- **Automation for Scale**: One command processes entire directories of videos, producing consistent, high-quality study material.
- **User Experience**: Thoughtful CLI design with progressive spinners and clean output.
- **Compliance & Reliability**: Uses open-source, well-supported tools with reproducible environments (`requirements.txt`).

---

## Example CLI Output

_The script dynamically shows the pipeline based on the source type:_

```bash
AI is warming up... ready to crunch some knowledge.

# Starting from Video
myVideo.mp4
    video > audio > transcript > study material > PDF

# Starting from Audio (no video exists)
lecture.mp3
    audio > transcript > study material > PDF

# Starting from Text (no video or audio exists)
notes.txt
    transcript > study material > PDF
```

---

## Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python video_transcribe.py ./data

# If you only want the Markdown study files and wish to skip PDF generation:
python video_transcribe.py ./data --no-pdf
```

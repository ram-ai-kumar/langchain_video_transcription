# LangChain Video Transcription & Study Material Generator

## Overview

This project began as a simple experiment: transcribing and understanding a few educational videos.  
It quickly evolved into a **fully automated pipeline** that transforms raw video content into **rich learning material** — complete with transcripts, structured summaries, glossaries, and practice questions — all orchestrated seamlessly.

The result is a system that demonstrates not only technical execution but also the **architectural thinking** required to design scalable, reliable, and extensible solutions.

---

## Features

- **Video → Audio Extraction**: Uses `ffmpeg` to isolate audio streams from video files.
- **Audio → Transcript**: Employs [OpenAI Whisper](https://github.com/openai/whisper) for accurate speech-to-text transcription.
- **Transcript → Summary**: Leverages [LangChain](https://www.langchain.com/) with Ollama LLM models to generate structured summaries with topics, headings, and concepts.
- **Summary → Study Material**:
  - Key concepts and definitions
  - Bullet-point notes
  - Glossary of important terms
  - 25 practice questions (MCQ + short answer)
- **Markdown → PDF**: Converts study material into polished PDFs using Pandoc + LaTeX.
- **CLI Experience**: Clean, readable, single-line progress updates with spinners for in-progress stages.

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

## Orchestration

The pipeline is designed as a **modular sequence of transformations**:

video → audio → transcript → summary → study material → PDF

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

_Each stage shows a rotating line as progress bar and ellipsis to denote in-progress_

```bash
AI is warming up... ready to crunch some knowledge.

myVideo.mp4
    video > ... |
    video > audio > ... /
    video > audio > text > markdown > study > PDF
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
python langchain_videos_transcription.py ./videos --pdf
```

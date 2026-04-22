# Usage

[← Back to README](../README.md)

---

## Supported Media Types

### Input

| Type   | Extensions                                                        |
| ------ | ----------------------------------------------------------------- |
| Video  | `.mp4`, `.mkv`, `.avi`, `.mov`                                    |
| Audio  | `.mp3`, `.wav`, `.m4a`, `.aac`                                    |
| Text   | `.txt`                                                            |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.webp` |

### Output

| Format         | Extension | Description                                          |
| -------------- | --------- | ---------------------------------------------------- |
| Transcript     | `.txt`    | Extracted text from audio/video/images               |
| Study Material | `.md`     | Structured study guide with glossary and questions   |
| PDF            | `.pdf`    | Formatted document (output only — not an input type) |

---

## Running the Pipeline

1. **Organize your content**
   - Create a folder such as `./data` and place your media inside it.
   - Mix any combination of video, audio, text, and image files.
   - Subfolders are allowed — the pipeline recursively walks the entire directory tree.
   - **Mixed folders are fully supported** — no need to separate media types.

2. **Run the script**

   ```bash
   # From the project root, with the virtualenv activated:
   python main.py ./data
   ```

   The pipeline scans the folder and renders a visual tree:

   ```text
   📁 data/
   ├── 📁 mobile_app/
   │   ├── [############################] ✓ login_flow.mp4
   │   └── [############################] ⏭ user_testing.mp3 (Skipped)
   └── [############################] ✓ overview.mp4
   ```

3. **Interactive Prompt or Explicit Targets**
   - Without `--target`, the CLI prompts for the desired output format interactively — allowing you to skip heavy AI models if you only need transcripts.
   - To run non-interactively, pass `--target` explicitly:

   ```bash
   # Stop at raw text transcripts — no LLM involved:
   python main.py ./data --target text

   # Stop at Markdown study material — no PDF rendering:
   python main.py ./data --target markdown
   ```

---

## Progress Display

The pipeline provides real-time progress tracking for each file being processed. Progress is displayed in-place on the same line and updates as processing advances through stages.

### Display Format

```bash
.../path/to/file.ext stage1 > stage2 > ... > stageN
```

- **Path Truncation**: Long paths are truncated to show only the last 3 directory levels
  - Short paths (≤3 levels): Full path shown
  - Long paths (4+ levels): `.../grandparent/parent/file.ext`
- **Past Stages**: Completed stages shown by name
- **Current Stage**: Actively processing stage shown as `...`
- **Future Stages**: Not displayed (cleaner, focused view)

### Processing Stages by File Type

| File Type | Processing Stages               |
| --------- | ------------------------------- |
| Video     | `audio > text > markdown > pdf` |
| Audio     | `text > markdown > pdf`         |
| Text      | `markdown > pdf`                |
| Images    | `text > markdown > pdf`         |

### Example Progress Flow

```bash
# During text-to-markdown generation:
.../UCDE05 - Cloud Development/004 Security Solution/003 On Premise and Hosted Solution 1.txt text > ...

# When markdown is ready and PDF generation starts:
.../UCDE05 - Cloud Development/004 Security Solution/003 On Premise and Hosted Solution 1.txt text > markdown > ...

# When processing is complete:
✓ .../UCDE05 - Cloud Development/004 Security Solution/003 On Premise and Hosted Solution 1.txt text > markdown > pdf
```

The progress display updates in-place, providing clean, real-time feedback without cluttering the terminal output.

1. **Inspect outputs** — for each logical item:
   - Transcript: `<name>.txt` (image OCR is cleanly appended to existing transcripts)
   - Study guide (Markdown): `<name>_study.md`
   - PDF (if enabled and Pandoc/Tectonic are installed): `<name>.pdf`

2. **Re-running is safe** — the pipeline is **idempotent**: existing artifacts are reused and only missing pieces are generated. Skipped files are reported as `[⏭ Skipped]`.

---

## Basic CLI Usage

```bash
# Process with default settings
python main.py /path/to/media/folder

# Skip PDF generation
python main.py /path/to/media/folder --no-pdf

# Show detailed progress
python main.py /path/to/media/folder --verbose

# Use different models
python main.py /path/to/media/folder --whisper-model large --llm-model llama3
```

## Advanced Options

```bash
# Specify output directory
python main.py /path/to/media/folder --output-dir /output/path

# Check dependencies
python main.py /path/to/media/folder --check-deps

# Validate files without processing
python main.py /path/to/media/folder --validate-only

# Use a configuration file
python main.py /path/to/media/folder --config config.json

# Disable progress spinner
python main.py /path/to/media/folder --no-spinner

# Performance overrides
python main.py /path/to/media/folder --device cuda --whisper-model large
```

---

## Configuration File

Create a JSON configuration file for complex or repeatable setups:

```json
{
  "whisper_model": "large",
  "llm_model": "qwen3.5:latest",
  "generate_pdf": true,
  "verbose": true,
  "output_dir": "/custom/output",
  "device": "auto"
}
```

---

## Customization

### Study Prompt (`config/study_prompt.txt`)

The AI's persona, output structure, and generation rules are defined in `config/study_prompt.txt`. Edit this file to:

- Change the tone of the generated textbook chapter.
- Add or remove sections from the study material.
- Update Bloom's Taxonomy-based question requirements.
- Change formatting or language requirements.

The file must contain a `{transcript}` placeholder where the source text will be injected.

---

## Example CLI Output

The pipeline dynamically renders the processing path based on detected media content:

```text
AI is warming up... ready to crunch some knowledge.

# Mixed Media Folder
lecture1.mp4
    video > audio > transcript > study material > PDF

slides01.png + slides01.jpg
    images (2) > transcript > study material > PDF

lecture1.mp4 + lecture1.png
    video > audio > transcript > study material > PDF
    images (1) > transcript > study material > PDF

random.gif (loose image)
    images (1) > transcript > study material > PDF
```

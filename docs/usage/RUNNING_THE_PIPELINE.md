# How to Run the Pipeline

[← Back to README](../README.md)

1. **Organize your content**
   - Create a folder such as `./data` and place your media inside it.
   - You can mix **any combination** of:
     - Video files (`.mp4`, `.mkv`, `.avi`, `.mov`)
     - Audio files (`.mp3`, `.wav`, `.m4a`, `.aac`)
     - Text transcripts (`.txt`)
     - Image files (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.webp`)
   - Subfolders are allowed; the script recursively walks the entire directory tree.
   - **Mixed folders are fully supported** — no need to separate media types.

2. **Run the script**

   ```bash
   # From the project root, with the virtualenv activated:
   python main.py ./data
   ```

   *The pipeline will scan your folder and produce a visual tree:*
   ```text
   📁 data/
   ├── 📁 mobile_app/
   │   ├── [############################] ✓ login_flow.mp4
   │   └── [############################] ⏭ user_testing.mp3 (Skipped)
   └── [############################] ✓ overview.mp4
   ```

3. **Interactive Prompt or Explicit Targets**
   - If you run the command above, the CLI will **interact and prompt you** for your desired destination format. You can avoid loading heavy AI models entirely if you just need Transcripts!
   - To bypass the prompt and run automatically, explicitly define your target using the `--target` (`-t`) flag:

   ```bash
   # Skip formatting and exit cleanly with raw text records:
   python main.py ./data --target text
   
   # Or extract to markdown without rendering Heavy PDFs:
   python main.py ./data --target markdown
   ```

4. **Inspect outputs**
   - For each logical item, you will find:
     - A transcript: `<name>.txt` (Image OCR is cleanly appended to existings transcripts)
     - A study guide (Markdown): `<name>_study.md`
     - A PDF (if enabled and Pandoc/LaTeX are installed): `<name>.pdf`

5. **Re-running is safe**
   - The pipeline is **idempotent**: existing artifacts are reused, and only missing pieces are generated.
   - If an artifact is skipped due to existing on disk, the terminal will cleanly report it as `[⏭ Skipped]`. 
   - Mixed media processing is deterministic and conflict-free.

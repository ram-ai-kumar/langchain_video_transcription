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

3. **Optional: skip PDF generation**

   ```bash
   python main.py ./data --no-pdf
   ```

4. **Inspect outputs**
   - For each logical item, you will find:
     - A transcript: `<name>.txt` or `<name>_images.txt` for image groups
     - A study guide (Markdown): `<name>_study.md` or `<name>_images_study.md`
     - A PDF (if enabled and Pandoc/LaTeX are installed): `<name>.pdf` or `<name>_images.pdf`

5. **Re-running is safe**
   - The pipeline is **idempotent**: existing artifacts are reused, and only missing pieces are generated.
   - Mixed media processing is deterministic and conflict-free.

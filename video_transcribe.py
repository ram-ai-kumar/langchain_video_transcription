"""End‑to‑end pipeline for turning videos, audio, text files, or image folders
into Markdown study material and optionally a PDF textbook‑style handout.

This script is designed to be run on a directory tree; it discovers media,
transcribes or OCRs it, generates an LLM‑authored study guide, and (optionally)
converts the result to a nicely formatted PDF via Pandoc/LaTeX.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import whisper
import pytesseract
from PIL import Image
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from langchain_core.runnables import RunnableSequence

VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov"]
AUDIO_EXTENSIONS = [".mp3", ".wav", ".m4a", ".aac"]
TEXT_EXTENSIONS = [".txt"]
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"]

spinner_cycle = ["|", "/", "-", "\\"]

def spinner(prefix, run_func, *args, **kwargs):
    """
    Show a lightweight CLI spinner while running a function or subprocess.

    The spinner runs in the main thread while `run_func` executes in a worker
    thread, and continuously rewrites the same console line for a clean UX.
    """
    done = False
    result = None
    exception = None

    def target():
        nonlocal result, exception
        try:
            result = run_func(*args, **kwargs)
        except Exception as e:
            exception = e

    import threading
    t = threading.Thread(target=target)
    t.start()

    i = 0
    while t.is_alive():
        sys.stdout.write(f"\r{prefix} {spinner_cycle[i % len(spinner_cycle)]}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    t.join()
    sys.stdout.write(f"\r{prefix}\n")
    sys.stdout.flush()
    
    if exception:
        raise exception
    return result

def extract_text_from_images(image_files, output_file):
    """
    Extract text from a list of image files using Tesseract OCR
    and write the combined text to a single output file.
    Images are processed in the order provided (caller should sort).
    """
    all_text = []
    for img_path in image_files:
        try:
            img = Image.open(img_path)
            text = pytesseract.image_to_string(img).strip()
            if text:
                all_text.append(text)
        except Exception as e:
            print(f"      [WARN] Could not OCR {img_path.name}: {e}")
    
    combined = "\n\n".join(all_text)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined)
    return output_file


def transcribe_audio(model, audio_file, transcript_file):
    """
    Transcribe a single audio file with a Whisper model and write plain text.

    Only the final concatenated transcript text is persisted; segment metadata
    from Whisper is intentionally discarded to keep downstream processing simple.
    """
    result = model.transcribe(str(audio_file), language="en", verbose=True)
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write(result["text"])
    return transcript_file

def process_pipeline(source_path, whisper_model, start_type, generate_pdf=True, llm_model="gemma3"):
    """
    Run the full processing pipeline for a single logical source (video/audio/text/images).

    - Derives standard output filenames (audio, transcript, study markdown, PDF)
      from the `source_path` stem.
    - Uses `start_type` to decide which stages are required:
      * ``video``  → extract audio → transcribe → study material → optional PDF
      * ``audio``  → transcribe → study material → optional PDF
      * ``text``   → study material → optional PDF
      * ``images`` → OCR to text → study material → optional PDF
    - Tracks a human‑readable list of steps for consistent status messages.
    """
    base = Path(source_path).stem
    dir_path = Path(source_path).parent

    audio_file = dir_path / f"{base}.mp3"
    transcript_file = dir_path / f"{base}.txt"
    study_file = dir_path / f"{base}_study.md"
    pdf_file = dir_path / f"{base}.pdf"

    print(f"\n{source_path.name}")

    steps = []

    # Step 1: Extract audio (only if starting from video)
    if start_type == "video":
        steps.append("video")
        if not audio_file.exists():
            spinner(f"    {' > '.join(steps)} > ...", subprocess.run,
                    ["ffmpeg", "-i", str(source_path),
                     "-vn", "-c:a", "libmp3lame", "-q:a", "2",
                     str(audio_file)], check=True)
        steps.append("audio")
    elif start_type == "audio":
        steps.append("audio")
    elif start_type == "text":
        steps.append("transcript")
    elif start_type == "images":
        steps.append("images")
        steps.append("transcript")

    # Step 2: Transcribe (if we have audio but no transcript).
    # This also covers the case where a transcript was deleted/re‑generated
    # while a compatible audio file is still present.
    if not transcript_file.exists() and (start_type in ["video", "audio"] or audio_file.exists()):
        if "audio" not in steps and audio_file.exists():
            steps.insert(0, "audio")
        
        spinner(f"    {' > '.join(steps)} > ...", transcribe_audio,
                whisper_model, audio_file, transcript_file)
    
    if "transcript" not in steps:
        steps.append("transcript")

    # Step 3: Study material (from transcript)
    if not study_file.exists():
        def study():
            # Load the study prompt from an external file
            prompt_path = Path(__file__).parent / "study_prompt.txt"
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt_template_text = f.read()
            except FileNotFoundError:
                print(f"    [ERROR] Prompt file not found: {prompt_path}")
                return

            study_prompt = PromptTemplate.from_template(prompt_template_text)
            # The LLM model is provided via Ollama; switching models only
            # requires changing the `llm_model` string.
            llm = OllamaLLM(model=llm_model)
            study_chain = RunnableSequence(first=study_prompt, last=llm)
            with open(transcript_file, "r", encoding="utf-8") as f:
                transcript_text = f.read()
            study_material = study_chain.invoke({"transcript": transcript_text})
            with open(study_file, "w", encoding="utf-8") as f:
                f.write(study_material)

        spinner(f"    {' > '.join(steps)} > ...", study)
    
    if "study material" not in steps:
        steps.append("study material")

    # Step 4: PDF (optional)
    if generate_pdf:
        if not pdf_file.exists():
            # Path to the LaTeX header file
            header_file = Path(__file__).parent / "header.tex"
            
            # Check if header file exists
            if not header_file.exists():
                print(f"    [WARN] Header file not found: {header_file}")
                return

            # Try XeLaTeX first for better Unicode support, fallback to pdfLaTeX
            engines = ["xelatex", "pdflatex"]
            
            for engine in engines:
                try:
                    if engine == "xelatex":
                        print(f"    [INFO] Trying XeLaTeX for better Unicode support...")
                        pandoc_command = [
                            "pandoc", str(study_file),
                            "-o", str(pdf_file),
                            "--pdf-engine=xelatex",
                            f"--include-in-header={str(header_file)}",
                            "--variable", "fontsize=12pt",
                            "--toc",  # Table of contents
                            "--toc-depth=3",
                            "--number-sections",
                            "--fail-if-warnings=false",  # Continue on non-critical warnings
                            "--log=INFO",  # Reduce verbosity
                            "--pdf-engine-opt=-interaction=nonstopmode",  # Don't stop on errors
                            "--pdf-engine-opt=-shell-escape",  # Allow shell escape if needed
                        ]
                    else:
                        print(f"    [INFO] Falling back to pdfLaTeX...")
                        pandoc_command = [
                            "pandoc", str(study_file),
                            "-o", str(pdf_file),
                            "--pdf-engine=pdflatex",
                            f"--include-in-header={str(header_file)}",
                            "--variable", "fontsize=12pt",
                            "--toc",  # Table of contents
                            "--toc-depth=3",
                            "--number-sections",
                            "--fail-if-warnings=false",  # Continue on non-critical warnings
                            "--log=INFO",  # Reduce verbosity
                            "--pdf-engine-opt=-interaction=nonstopmode",  # Don't stop on errors
                            "--pdf-engine-opt=-shell-escape",  # Allow shell escape if needed
                        ]

                    spinner(f"    {' > '.join(steps)} > PDF ({engine}) ...", subprocess.run,
                            pandoc_command, check=True, capture_output=True, text=True)
                    print(f"    [SUCCESS] PDF generation succeeded with {engine}")
                    break  # Success, exit the engine loop
                    
                except subprocess.CalledProcessError as e:
                    print(f"    [ERROR] PDF generation failed with {engine} for {study_file.name}")
                    print(f"    [ERROR] Pandoc exit code: {e.returncode}")
                    
                    # Extract error messages
                    error_output = ""
                    if e.stderr:
                        error_output = str(e.stderr)
                    elif e.stdout:
                        error_output = str(e.stdout)
                    
                    # Provide helpful error messages based on common issues
                    if error_output:
                        if "Permission denied" in error_output:
                            print(f"    [ERROR] Permission denied - check write permissions for {pdf_file.parent}")
                        elif "No such file" in error_output or "cannot find" in error_output.lower():
                            print(f"    [ERROR] Missing file or directory - check paths")
                            print(f"    [ERROR] Input file: {study_file}")
                            print(f"    [ERROR] Output file: {pdf_file}")
                        elif "Undefined control sequence" in error_output:
                            print(f"    [ERROR] LaTeX syntax error in markdown file")
                            # Show the problematic line if available
                            lines = error_output.split('\n')
                            for line in lines:
                                if "Undefined control sequence" in line:
                                    print(f"    [ERROR] {line[:150]}")
                        elif "LaTeX Error" in error_output or "Unicode character" in error_output:
                            print(f"    [ERROR] LaTeX compilation error detected")
                            # Show first few error lines
                            error_lines = [l for l in error_output.split('\n') if 'Error' in l or 'Fatal' in l or 'Unicode' in l][:3]
                            for line in error_lines:
                                print(f"    [ERROR] {line[:150]}")
                        else:
                            # Show last 500 chars of error output for debugging
                            print(f"    [ERROR] Error details: {error_output[-500:]}")
                    
                    # Common Pandoc exit codes
                    if e.returncode == 6:
                        print(f"    [ERROR] LaTeX compilation failed (exit code 6)")
                        print(f"    [INFO] This often indicates LaTeX syntax errors or missing packages")
                    elif e.returncode == 43:
                        print(f"    [ERROR] LaTeX compilation error - possibly special characters in content")
                    
                    # If this was the last engine, try simple fallback
                    if engine == engines[-1]:
                        print(f"    [INFO] All engines failed, trying minimal PDF generation...")
                        try:
                            fallback_command = [
                                "pandoc", str(study_file),
                                "-o", str(pdf_file),
                                "--pdf-engine=pdflatex",
                                "--variable", "fontsize=12pt",
                                "--fail-if-warnings=false",
                                "--pdf-engine-opt=-interaction=nonstopmode"
                            ]
                            spinner(f"    {' > '.join(steps)} > PDF (minimal) ...", subprocess.run,
                                    fallback_command, check=True, capture_output=True, text=True)
                            print(f"    [SUCCESS] Minimal PDF generation succeeded")
                        except subprocess.CalledProcessError as fallback_error:
                            print(f"    [ERROR] Minimal PDF generation also failed (exit code: {fallback_error.returncode})")
                            if fallback_error.stderr:
                                print(f"    [ERROR] Minimal fallback error: {str(fallback_error.stderr)[-300:]}")
                            print(f"    [INFO] Continuing without PDF generation...")
                            if "PDF" not in steps:
                                steps.append("PDF (failed)")
                        except Exception as fallback_exception:
                            print(f"    [ERROR] Unexpected error in minimal fallback: {fallback_exception}")
                            print(f"    [INFO] Continuing without PDF generation...")
                            if "PDF" not in steps:
                                steps.append("PDF (failed)")
                    else:
                        # Try next engine
                        continue
                        
                except Exception as e:
                    print(f"    [ERROR] Unexpected error during PDF generation with {engine}: {e}")
                    if engine == engines[-1]:  # Last engine
                        print(f"    [INFO] Continuing without PDF generation...")
                        if "PDF" not in steps:
                            steps.append("PDF (failed)")
                    else:
                        continue
        
        if "PDF" not in steps:
            steps.append("PDF")

    # Final pipeline line
    print("    " + " > ".join(steps))


def process_directory(directory, whisper_model, generate_pdf=True):
    """
    Walk a directory tree and run `process_pipeline` for each logical source.

    Processing happens in three passes:
    1. Video/audio/text groups: Processed by stem with priority (video > audio > text)
    2. Image groups: Processed by stem, including those sharing stems with other media
    3. Loose images: Images without matching stems grouped by folder name
    
    Images sharing a stem with video/audio/text use `{stem}_images.txt` naming
    to avoid conflicts. Images with unique stems use `{stem}.txt`.
    
    Grouping is done by filename stem within each folder so that, for example,
    ``lecture1.mp4`` and ``lecture1.mp3`` are treated as the same logical item,
    while ``lecture1.mp4`` and ``lecture1.png`` produce separate transcripts.
    """
    dir_path = Path(directory)
    
    # Traverse through all subdirectories using os.walk so the user can point
    # the tool at a single top‑level content root. We sort directory names
    # case‑insensitively so that folders are visited in chronological/
    # lexicographic name order by their name.
    for root, dirs, _ in os.walk(dir_path):
        dirs.sort(key=lambda d: d.lower())
        current_dir = Path(root)
        
        # Collect and sort all files in this directory by name (case‑insensitive)
        # so that per‑folder processing also follows chronological/lexicographic
        # order of their name.
        all_files = sorted(
            [f for f in current_dir.iterdir() if f.is_file()],
            key=lambda f: f.name.lower(),
        )
        if not all_files:
            continue

        # Group files by stem for all media types including images
        groups = {}
        for file in all_files:
            groups.setdefault(file.stem, []).append(file)

        # Track which stems have been processed (for conflict detection)
        processed_stems = set()
        
        # First pass: Process video/audio/text groups (priority: video > audio > text)
        for stem in sorted(groups.keys(), key=lambda s: s.lower()):
            files = groups[stem]
            video_file = next((f for f in files if f.suffix.lower() in VIDEO_EXTENSIONS), None)
            audio_file = next((f for f in files if f.suffix.lower() in AUDIO_EXTENSIONS), None)
            text_file = next((f for f in files if f.suffix.lower() in TEXT_EXTENSIONS), None)
            
            source_path = None
            start_type = None
            
            if video_file:
                source_path = video_file
                start_type = "video"
            elif audio_file:
                source_path = audio_file
                start_type = "audio"
            elif text_file:
                source_path = text_file
                start_type = "text"
            
            if source_path:
                try:
                    process_pipeline(source_path, whisper_model, start_type, generate_pdf=generate_pdf)
                    processed_stems.add(stem)
                except Exception as e:
                    print(f"    [ERROR] Could not process {stem} in {current_dir}: {e}")

        # Second pass: Process image groups (including those sharing stems with processed media)
        for stem in sorted(groups.keys(), key=lambda s: s.lower()):
            files = groups[stem]
            image_files = [f for f in files if f.suffix.lower() in IMAGE_EXTENSIONS]
            
            if image_files:
                # Determine transcript filename: use _images suffix if stem conflicts with processed media
                if stem in processed_stems:
                    transcript_file = current_dir / f"{stem}_images.txt"
                else:
                    transcript_file = current_dir / f"{stem}.txt"
                
                try:
                    if not transcript_file.exists():
                        print(f"\n  [OCR] {stem}/ ({len(image_files)} images)")
                        spinner(
                            f"    images ({len(image_files)}) > transcript ...",
                            extract_text_from_images, image_files, transcript_file
                        )
                    process_pipeline(transcript_file, whisper_model, "images", generate_pdf=generate_pdf)
                    processed_stems.add(stem)
                except Exception as e:
                    print(f"    [ERROR] Could not process images for {stem} in {current_dir}: {e}")

        # Third pass: Process remaining loose images (those not matching any stem group)
        all_image_files = [f for f in all_files if f.suffix.lower() in IMAGE_EXTENSIONS]
        unprocessed_images = [f for f in all_image_files if f.stem not in processed_stems]
        
        if unprocessed_images:
            # Use the folder name as the base name for the text file
            folder_name = current_dir.name
            transcript_file = current_dir / f"{folder_name}_images.txt"
            
            if not transcript_file.exists():
                print(f"\n  [OCR] {folder_name}/ ({len(unprocessed_images)} loose images)")
                spinner(
                    f"    images ({len(unprocessed_images)}) > transcript ...",
                    extract_text_from_images, unprocessed_images, transcript_file
                )
            
            # Now process the generated text file through the pipeline
            try:
                process_pipeline(transcript_file, whisper_model, "images", generate_pdf=generate_pdf)
            except Exception as e:
                print(f"    [ERROR] Could not process loose images in {current_dir}: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process videos into study material/PDFs")
    parser.add_argument("directory", help="Path to folder containing video files")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation (PDF generated by default)")
    args = parser.parse_args()

    # CLI entry point: load Whisper once, then process the entire directory tree.
    print("AI is warming up... ready to crunch some knowledge.")

    whisper_model = whisper.load_model("medium")

    process_directory(args.directory, whisper_model, generate_pdf=not args.no_pdf)

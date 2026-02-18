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

    def target():
        nonlocal result
        result = run_func(*args, **kwargs)

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
            # Large, single PromptTemplate that tells the LLM to ignore lecture
            # structure and instead author a standalone textbook‑style chapter.
            study_prompt = PromptTemplate.from_template(
                "You are a world-class domain expert and textbook author. A transcript from a lecture is provided below.\n\n"
                "### YOUR TASK (Two Phases):\n\n"
                "**Phase 1 — Concept Extraction:**\n"
                "Read the transcript and identify the core SUBJECT DOMAIN, TOPICS, and CONCEPTS being discussed. "
                "The transcript is ONLY a source of topic hints — do NOT summarize, paraphrase, or follow the structure of the transcript.\n\n"
                "**Phase 2 — Authoritative Content Generation:**\n"
                "Write a comprehensive, standalone textbook chapter that teaches these topics in depth — as if you are writing for a professional reference book, NOT summarizing a lecture. "
                "You must write ORIGINAL, AUTHORITATIVE content about the identified topics.\n\n"
                "### CRITICAL RULES:\n"
                "1. **NEVER reference the transcript, lecture, video, speaker, presentation, or recording.** Do not use phrases like 'In this video', 'The speaker explains', 'As discussed in the lecture', 'The presenter mentions'. Write as if no transcript exists.\n"
                "2. **Do NOT follow the transcript's structure or flow.** Organize content by the logical structure of the DOMAIN KNOWLEDGE itself.\n"
                "3. **Go BEYOND what was said.** For each concept:\n"
                "   - Define it precisely and explain why it matters\n"
                "   - Describe types, classifications, or variations\n"
                "   - Explain how to implement or apply it step by step\n"
                "   - List common mistakes and pitfalls and how to avoid them\n"
                "   - Reference relevant industry standards, frameworks, or best practices\n"
                "   - Provide practical real-world examples\n"
                "4. **Write like a textbook author**, not a note-taker. Every section should teach the reader something they can apply.\n"
                "5. **Professional Tone**: Maintain a formal, academic, yet engaging tone suitable for a professional study guide.\n"
                "6. **Formatting**: Use clean Markdown with clear hierarchies. Ensure mathematical formulas or code snippets are in appropriate blocks.\n\n"
                "### STRUCTURE YOUR RESPONSE WITH THESE SECTIONS:\n\n"
                "# [Authoritative Title for the Subject Domain]\n\n"
                "## 1. Learning Objectives\n"
                "List 3-5 clear, actionable objectives. What will the reader be able to DO after mastering this material?\n\n"
                "## 2. Executive Overview\n"
                "A detailed 2-3 paragraph introduction to the subject domain. Why does this topic matter? What problems does it solve? Where does it fit in the broader field?\n\n"
                "## 3. Core Concepts & Technical Definitions\n"
                "Define each fundamental concept with precision. Use **bold** for key terms. For each term, include: definition, significance, and how it relates to other concepts.\n\n"
                "## 4. In-Depth Subject Matter Coverage\n"
                "This is the main body. Organize by DOMAIN LOGIC, not by transcript order. Use logical headings (###) and sub-headings (####). For each major topic:\n"
                "- Explain the concept thoroughly with first-principles reasoning\n"
                "- Provide step-by-step processes or methodologies where applicable\n"
                "- Include **Best Practices** callouts with actionable recommendations\n"
                "- Include **Common Pitfalls** callouts warning about frequent mistakes\n"
                "- Use blockquotes (>) for real-world scenarios, case studies, or analogies\n"
                "- Reference industry standards and frameworks (e.g., NIST, ISO, IEEE, OWASP, etc.) where relevant\n"
                "- Use code blocks (```) for any technical syntax, commands, or formulas\n\n"
                "## 5. Summary & Actionable Takeaways\n"
                "Synthesize the most critical knowledge into a 'Key Takeaways' list. Focus on what the reader should remember and apply immediately.\n\n"
                "## 6. Glossary of Terms\n"
                "A comprehensive list of technical terms with expanded definitions, context, and cross-references to related terms.\n\n"
                "## 7. Knowledge Assessment (Bloom's Taxonomy Based)\n"
                "Provide a robust set of questions to test different levels of understanding:\n\n"
                "### Part A: Recall & Comprehension (10 MCQs)\n"
                "Test foundational knowledge of the domain concepts.\n"
                "**Q1:** Question?\n"
                "- A) Option\n"
                "- B) Option\n"
                "- C) **Option (Correct)**\n"
                "- D) Option\n\n"
                "### Part B: Application & Analysis (5 Short Answer Questions)\n"
                "Present realistic scenarios requiring the reader to apply domain knowledge.\n"
                "**Q11:** Scenario/Question text?\n"
                "*Answer:* Detailed explanation demonstrating practical application.\n\n"
                "### Part C: Synthesis & Evaluation (2 Critical Thinking Challenges)\n"
                "Require the reader to design solutions, compare approaches, or evaluate trade-offs.\n"
                "**Q16:** Challenge prompt?\n"
                "*Answer:* Guidelines for a high-quality response.\n\n"
                "---\n"
                "REMEMBER: You are a domain expert writing a textbook chapter. The transcript below is ONLY used to identify WHAT topics to cover. "
                "Your content must be original, authoritative, and comprehensive — teach the reader the subjects as an expert would.\n\n"
                "Transcript (for topic identification only):\n"
                "{transcript}"
            )
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

            pandoc_command = [
                "pandoc", str(study_file),
                "-o", str(pdf_file),
                "--pdf-engine=pdflatex",
                f"--include-in-header={str(header_file)}",
                "--variable", "fontsize=12pt",
                "--toc",  # Table of contents
                "--toc-depth=3",
                "--number-sections"
            ]

            spinner(f"    {' > '.join(steps)} > PDF ...", subprocess.run,
                    pandoc_command, check=True)
        
        if "PDF" not in steps:
            steps.append("PDF")

    # Final pipeline line
    print("    " + " > ".join(steps))


def process_directory(directory, whisper_model, generate_pdf=True):
    """
    Walk a directory tree and run `process_pipeline` for each logical source.

    Grouping is done by filename stem within each folder so that, for example,
    ``lecture1.mp4`` and ``lecture1.mp3`` are treated as the same logical item
    with a clear precedence order (video > audio > existing text).
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

        # Group files by stem for video/audio/text processing
        groups = {}
        for file in all_files:
            groups.setdefault(file.stem, []).append(file)

        # Check if this folder has processable sources (video/audio/text)
        has_processable = any(
            any(f.suffix.lower() in VIDEO_EXTENSIONS + AUDIO_EXTENSIONS + TEXT_EXTENSIONS for f in files)
            for files in groups.values()
        )

        if has_processable:
            # Standard processing: Video > Audio > Text priority per stem group.
            # Iterate stems in sorted (case‑insensitive) order so logical items
            # are handled chronologically by their base name.
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
                    except Exception as e:
                        print(f"    [ERROR] Could not process {stem} in {current_dir}: {e}")
        else:
            # Fallback for image‑only folders: treat them as slide decks or
            # scanned pages and build a transcript via OCR before piping them
            # through the normal text pipeline.
            image_files = sorted(
                [f for f in all_files if f.suffix.lower() in IMAGE_EXTENSIONS],
                key=lambda f: f.name.lower()
            )
            if image_files:
                # Use the folder name as the base name for the text file
                folder_name = current_dir.name
                transcript_file = current_dir / f"{folder_name}.txt"
                
                if not transcript_file.exists():
                    print(f"\n  [OCR] {folder_name}/ ({len(image_files)} images)")
                    spinner(
                        f"    images ({len(image_files)}) > transcript ...",
                        extract_text_from_images, image_files, transcript_file
                    )
                
                # Now process the generated text file through the pipeline
                try:
                    process_pipeline(transcript_file, whisper_model, "images", generate_pdf=generate_pdf)
                except Exception as e:
                    print(f"    [ERROR] Could not process images in {current_dir}: {e}")


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

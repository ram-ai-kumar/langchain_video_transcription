import os
import sys
import subprocess
import time
from pathlib import Path
import whisper
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from langchain_core.runnables import RunnableSequence

VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov"]
AUDIO_EXTENSIONS = [".mp3", ".wav", ".m4a", ".aac"]
TEXT_EXTENSIONS = [".txt"]
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"]

spinner_cycle = ["|", "/", "-", "\\"]

def spinner(prefix, run_func, *args, **kwargs):
    """
    Show spinner while running a function or subprocess.
    Updates the same line in place.
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

def transcribe_audio(model, audio_file, transcript_file):
    result = model.transcribe(str(audio_file), language="en", verbose=True)
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write(result["text"])
    return transcript_file

def extract_text_from_images(image_files, output_txt):
    """
    OCR all image files (sorted to preserve page order), merge extracted text
    into a single output .txt file separated by double newlines between pages.
    image_files: list of Path objects
    output_txt: Path object for the merged output text file
    """
    import pytesseract
    from PIL import Image

    pages = []
    for img_path in sorted(image_files):
        img = Image.open(img_path)
        text = pytesseract.image_to_string(img).strip()
        if text:
            pages.append(text)

    with open(output_txt, "w", encoding="utf-8") as f:
        f.write("\n\n".join(pages))

    return output_txt

def process_pipeline(source_path, whisper_model, start_type, generate_pdf=True, llm_model="gemma3"):
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

    # Step 2: Transcribe (if we have audio but no transcript)
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
            study_prompt = PromptTemplate.from_template(
                "You are a subject matter expert and textbook author. You have been given raw notes extracted from a knowledge source on a technical topic.\n"
                "Your task is to write a comprehensive, standalone textbook chapter on the subject matter covered in those notes.\n\n"
                "### ABSOLUTE RULES — NEVER VIOLATE THESE:\n"
                "1. **Never review or evaluate the source material.** Do not comment on how the material was presented, structured, or delivered.\n"
                "2. **Never mention the source.** Do not reference the speaker, presenter, video, session, lecture, recording, poll, audience, or any meta-context about where this content came from.\n"
                "3. **Never use phrases like** 'this presentation covers...', 'the speaker explains...', 'as mentioned in the session...', 'this lecture discusses...', or anything similar.\n"
                "4. **Write only educational content.** You are the expert. Write as if you are authoring a university textbook chapter.\n"
                "5. **Expand beyond the notes.** The raw notes are a starting point. You must enrich the content with your own expert knowledge: relevant industry standards, frameworks, best practices, real-world examples, common pitfalls, and deeper technical detail than what the notes contain.\n\n"
                "### APPROACH:\n"
                "First, identify the core subject domain and all technical topics mentioned in the notes.\n"
                "Then write a complete, authoritative textbook chapter that teaches those topics comprehensively.\n\n"
                "### STRUCTURE YOUR CHAPTER WITH THESE SECTIONS:\n\n"
                "# [Authoritative Title: The Subject Matter Itself — e.g., 'Security Architecture: Design, Frameworks, and Implementation']\n\n"
                "## 1. Introduction & Why It Matters\n"
                "Establish the importance of this subject in the real world. Why does a professional need to understand this? What problems does it solve?\n\n"
                "## 2. Learning Objectives\n"
                "List 5-7 specific, measurable objectives a student will achieve after studying this chapter.\n\n"
                "## 3. Core Concepts & Technical Definitions\n"
                "Define every key term and concept in the subject area. Use **bold** for terms. Provide precise, textbook-quality definitions with context.\n\n"
                "## 4. In-Depth Technical Coverage\n"
                "This is the main body. For each major topic or sub-topic identified in the notes, create a dedicated sub-section (###) covering:\n"
                "- **What it is**: Clear definition and purpose\n"
                "- **How it works**: Technical mechanism or process\n"
                "- **Types and variants**: All major categories with differences explained\n"
                "- **Industry standards and frameworks**: Relevant standards (e.g., NIST, ISO, OWASP) and how they apply\n"
                "- **Implementation guidance**: How to deploy or apply this in practice\n"
                "- **Best practices**: What experts recommend\n"
                "- **Common pitfalls**: What to avoid and why\n"
                "Use blockquotes (>) for real-world examples or analogies. Use code blocks (```) for technical syntax or configuration examples.\n\n"
                "## 5. Practical Application & Case Studies\n"
                "Provide 2-3 realistic scenarios showing how these concepts apply in professional settings.\n\n"
                "## 6. Key Takeaways\n"
                "A concise list of the most important points a professional must remember and be able to apply.\n\n"
                "## 7. Glossary of Terms\n"
                "Alphabetical list of all technical terms with expanded definitions and usage context.\n\n"
                "## 8. Knowledge Assessment (Bloom's Taxonomy Based)\n"
                "Provide rigorous questions testing different cognitive levels:\n\n"
                "### Part A: Recall & Comprehension (10 MCQs)\n"
                "Test factual knowledge and conceptual understanding.\n"
                "**Q1:** Question about the subject matter?\n"
                "- A) Option\n"
                "- B) Option\n"
                "- C) **Option (Correct)**\n"
                "- D) Option\n\n"
                "### Part B: Application & Analysis (5 Short Answer Questions)\n"
                "Present scenarios requiring the student to apply or analyze concepts.\n"
                "**Q11:** Realistic scenario requiring application of knowledge?\n"
                "*Answer:* Detailed model answer demonstrating correct application.\n\n"
                "### Part C: Synthesis & Evaluation (2 Critical Thinking Challenges)\n"
                "Require the student to design solutions or evaluate trade-offs.\n"
                "**Q16:** Open-ended challenge requiring expert-level thinking?\n"
                "*Answer:* Criteria and guidance for a high-quality response.\n\n"
                "Raw notes to extract knowledge from:\n"
                "{transcript}"
            )
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

    # Step 4: PDF
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
    dir_path = Path(directory)

    # Traverse through all subdirectories using os.walk
    for root, dirs, _ in os.walk(dir_path):
        current_dir = Path(root)

        # --- IMAGE BATCH PASS (folder-level) ---
        # All images in a directory are treated as pages of one document.
        # They are OCR'd, merged into a single .txt named after the folder,
        # then fed into the existing text → study material → PDF pipeline.
        image_files = [
            f for f in current_dir.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ]
        if image_files:
            folder_name = current_dir.name
            merged_txt = current_dir / f"{folder_name}.txt"
            if not merged_txt.exists():
                spinner(f"    images > ...", extract_text_from_images, image_files, merged_txt)
            # Only continue to study material if no richer source (video/audio) exists in this folder
            has_richer_source = any(
                f.suffix.lower() in VIDEO_EXTENSIONS + AUDIO_EXTENSIONS
                for f in current_dir.iterdir() if f.is_file()
            )
            if not has_richer_source:
                try:
                    process_pipeline(merged_txt, whisper_model, "text", generate_pdf=generate_pdf)
                except Exception as e:
                    print(f"    [ERROR] Image OCR pipeline failed in {current_dir}: {e}")

        # --- PER-STEM PASS: Video / Audio / Text (unchanged) ---
        # Group files in the current folder by stem
        groups = {}
        for file in current_dir.iterdir():
            if file.is_file():
                groups.setdefault(file.stem, []).append(file)

        if not groups:
            continue

        for stem, files in groups.items():
            # Priority for entry point: Video > Audio > Text
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


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process videos into study material/PDFs")
    parser.add_argument("directory", help="Path to folder containing video files")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation (PDF generated by default)")
    args = parser.parse_args()

    print("AI is warming up... ready to crunch some knowledge.")

    whisper_model = whisper.load_model("medium")

    process_directory(args.directory, whisper_model, generate_pdf=not args.no_pdf)

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
                "You are an expert educator and instructional designer. Your goal is to transform the following lecture transcript into a comprehensive, high-quality textbook-style learning module.\n\n"
                "### CRITICAL GUIDELINES:\n"
                "1. **Subject Matter Focus**: Focus exclusively on the educational content, concepts, and technical details. Do NOT mention the video, the trainer, the recording, or the fact that this is a transcript (e.g., avoid 'In this video', 'The speaker explains').\n"
                "2. **Comprehensive Depth**: Do not just summarize; expand on the concepts. If a concept is mentioned, explain it thoroughly. Use analogies or examples where helpful to clarify complex points.\n"
                "3. **Professional Tone**: Maintain a formal, academic, yet engaging tone suitable for a professional study guide.\n"
                "4. **Formatting**: Use clean Markdown with clear hierarchies. Ensure mathematical formulas or code snippets are in appropriate blocks.\n\n"
                "### STRUCTURE YOUR RESPONSE WITH THESE SECTIONS:\n\n"
                "# [Title Based on Subject Matter]\n\n"
                "## 1. Learning Objectives\n"
                "List 3-5 clear objectives that a student will achieve after studying this material.\n\n"
                "## 2. Executive Overview\n"
                "Provide a detailed 1-2 paragraph summary of the core themes and the importance of the topic.\n\n"
                "## 3. Core Concepts & Technical Definitions\n"
                "Identify and define the fundamental building blocks mentioned. Use **bold** for terms and provide clear, concise definitions.\n\n"
                "## 4. Comprehensive Subject Matter Notes\n"
                "This is the main body. Organize with logical headings (###) and sub-headings (####). Use:\n"
                "- Deep dives into specific sub-topics.\n"
                "- **Analogy/Example Boxes**: Use blockquotes (>) for real-world scenarios or analogies that help explain difficult concepts.\n"
                "- Bulleted lists for processes or features.\n"
                "- Code blocks (```) for any technical syntax, commands, or formulas.\n\n"
                "## 5. Summary & Actionable Takeaways\n"
                "Synthesize the most important points into a 'Key Takeaways' list. What are the immediate applications of this knowledge?\n\n"
                "## 6. Glossary of Terms\n"
                "A comprehensive list of technical terms with expanded definitions and context.\n\n"
                "## 7. Knowledge Assessment (Bloom's Taxonomy Based)\n"
                "Provide a robust set of questions to test different levels of understanding:\n\n"
                "### Part A: Recall & Comprehension (10 MCQs)\n"
                "Focus on facts and basic concepts.\n"
                "**Q1:** Question?\n"
                "- A) Option\n"
                "- B) Option\n"
                "- C) **Option (Correct)**\n"
                "- D) Option\n\n"
                "### Part B: Application & Analysis (5 Short Answer Questions)\n"
                "Focus on how to use the knowledge or analyze scenarios.\n"
                "**Q11:** Scenario/Question text?\n"
                "*Answer:* Detailed explanation of the application/analysis.\n\n"
                "### Part C: Synthesis & Evaluation (2 Critical Thinking Challenges)\n"
                "Ask the student to combine ideas or judge the value of information.\n"
                "**Q16:** Challenge prompt?\n"
                "*Answer:* Guidelines for a high-quality response.\n\n"
                "Transcript content to process:\n"
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
    
    # Group files by stem to identify candidates for processing
    groups = {}
    for file in dir_path.iterdir():
        if file.is_file():
            groups.setdefault(file.stem, []).append(file)
            
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
                print(f"    [ERROR] Could not process {stem}: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process videos into study material/PDFs")
    parser.add_argument("directory", help="Path to folder containing video files")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation (PDF generated by default)")
    args = parser.parse_args()

    print("AI is warming up... ready to crunch some knowledge.")

    whisper_model = whisper.load_model("medium")

    process_directory(args.directory, whisper_model, generate_pdf=not args.no_pdf)

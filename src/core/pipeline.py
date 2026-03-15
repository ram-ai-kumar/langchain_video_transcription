"""Main pipeline orchestrator for video transcription and study material generation."""

import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional, Set
import whisper

from src.core.config import PipelineConfig
from src.core.exceptions import VideoTranscriptionError, ProcessingError
from src.generators.study_generator import StudyMaterialGenerator
from src.processors.audio_processor import AudioProcessor
from src.processors.image_processor import ImageProcessor
from src.processors.text_processor import TextProcessor
from src.processors.base import ProcessResult
from src.utils.file_utils import FileDiscovery, FileManager
from src.utils.ui_utils import ProgressReporter, StatusReporter, PROCESSING_STEPS
from src.utils.media_utils import MediaTypeDetector, MediaProcessorFactory


def setup_logging(verbose: bool = False) -> None:
    """Configure application-wide logging.

    Args:
        verbose: If True, set log level to DEBUG; otherwise INFO
    """
    # Determine log level based on verbosity
    log_level = logging.DEBUG if verbose else logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    logging.getLogger('whisper').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('langchain').setLevel(logging.WARNING)
    logging.getLogger('langchain_core').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

    # Suppress Python 3.14 compatibility warnings
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, message=".*Core Pydantic V1 functionality isn't compatible with Python 3.14.*")


class VideoTranscriptionPipeline:
    """Main pipeline coordinator that manages the entire processing workflow."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.whisper_model: Optional[whisper.Whisper] = None
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.file_discovery = FileDiscovery(config)
        self.study_generator = StudyMaterialGenerator(config)
        self.status_reporter = StatusReporter(config.verbose)
        self.progress_reporter = ProgressReporter(config.verbose)

        # Initialize processors
        self.audio_processor = AudioProcessor(config)
        self.image_processor = ImageProcessor(config)
        self.text_processor = TextProcessor(config)

        # Media type detection
        self.media_detector = MediaTypeDetector(config)

        # Track processed items
        self.processed_stems: Set[str] = set()

    def _load_whisper_model(self) -> whisper.Whisper:
        """Load Whisper model if not already loaded."""
        if self.whisper_model is None:
            try:
                # Load Whisper model
                import torch
                if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    device = "mps"
                elif torch.cuda.is_available():
                    device = "cuda"
                else:
                    device = "cpu"
                import warnings
                import os
                import logging
                # Suppress all Whisper warnings and progress output
                os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning'
                os.environ['TQDM_DISABLE'] = '1'  # Disable tqdm progress bars
                logging.getLogger('whisper').setLevel(logging.ERROR)  # Suppress whisper logging
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self.whisper_model = whisper.load_model(
                        self.config.whisper_model,
                        device=device
                    )

                self.status_reporter.info(f"Loaded Whisper model: {self.config.whisper_model} (device: {device})")
            except Exception as e:
                raise VideoTranscriptionError(f"Failed to load Whisper model '{self.config.whisper_model}': {e}")
        return self.whisper_model

    def process_directory(self, directory: Path) -> ProcessResult:
        """Process entire directory tree."""
        try:
            if not directory.exists():
                raise FileNotFoundError(f"Directory not found: {directory}")

            self.status_reporter.info(f"Starting directory processing: {directory}")

            file_groups = self.file_discovery.group_files_by_stem(directory)

            if not file_groups:
                return ProcessResult(
                    success=True,
                    message="No supported files found in directory",
                    metadata={"directory": str(directory), "groups_found": 0}
                )

            self.status_reporter.info(f"Found {len(file_groups)} file groups to process")

            tree = {}

            # Helper to add task to tree
            def add_task(file_path, task):
                try:
                    rel_path = file_path.relative_to(directory)
                except ValueError:
                    rel_path = file_path.name

                parts = rel_path.parts

                current = tree
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                task_key = f"__task__{task['name']}"
                current[task_key] = task

            # 1. Media groups
            for group_key in sorted(file_groups.keys(), key=lambda k: k.lower()):
                files = file_groups[group_key]
                source_path, start_type = self.file_discovery.find_primary_source(files)
                if source_path and start_type in ["video", "audio", "text"]:
                    add_task(source_path, {
                        "type": "media",
                        "name": source_path.name,
                        "source_path": source_path,
                        "start_type": start_type,
                        "stem": source_path.stem
                    })

            # 2. Image groups
            for group_key in sorted(file_groups.keys(), key=lambda k: k.lower()):
                files = file_groups[group_key]
                image_files = self.file_discovery.separate_image_files(files)
                if not image_files:
                    continue

                stem = group_key.split("::")[-1] if "::" in group_key else group_key
                target_dir = image_files[0].parent
                transcript_file = target_dir / f"{stem}.txt"

                add_task(transcript_file, {
                    "type": "image_group",
                    "name": transcript_file.name + " (Images)",
                    "stem": stem,
                    "image_files": image_files,
                    "transcript_file": transcript_file
                })

            # 3. Loose images
            all_files = self.file_discovery.discover_files(directory)
            all_image_files = [f for f in all_files if self.config.is_image_file(f)]

            # Pre-calculate processed stems to isolate loose images
            processed_stems_pre = set()
            for group_key, files in file_groups.items():
                source_path, start_type = self.file_discovery.find_primary_source(files)
                if source_path and start_type in ["video", "audio", "text"]:
                    processed_stems_pre.add(source_path.stem)

                image_files_sep = self.file_discovery.separate_image_files(files)
                if image_files_sep:
                    stem = group_key.split("::")[-1] if "::" in group_key else group_key
                    processed_stems_pre.add(stem)

            unprocessed_images = [f for f in all_image_files if f.stem not in processed_stems_pre]

            dir_loose_groups = {}
            for img_path in unprocessed_images:
                dir_loose_groups.setdefault(img_path.parent, []).append(img_path)

            for dir_path, images in dir_loose_groups.items():
                folder_name = dir_path.name
                transcript_file = dir_path / f"{folder_name}.txt"
                add_task(transcript_file, {
                    "type": "loose_images",
                    "name": transcript_file.name + " (Loose Images)",
                    "folder_name": folder_name,
                    "images": images,
                    "transcript_file": transcript_file
                })

            processed_count = [0]
            error_count = [0]
            processed_stems = set()

            print(f"\n📁 {directory.name}/")

            def execute_task(task, prefix_for_progress):
                try:
                    if task["type"] == "media":
                        steps = PROCESSING_STEPS.get(task["start_type"], ["transcript", "study_material", "pdf"])
                        self.progress_reporter.start_processing(task["name"], steps, prefix_for_progress)
                        result = self.process_single_source(task["source_path"], task["start_type"])
                        self.progress_reporter.complete_processing(result.success)

                        if result.success:
                            processed_count[0] += 1
                            processed_stems.add(task["stem"])
                            self.processed_stems.add(task["stem"])
                        else:
                            error_count[0] += 1
                            self.status_reporter.error(f"Failed to process {task['name']}: {result.message}")

                    elif task["type"] == "image_group":
                        steps = PROCESSING_STEPS.get("image", ["transcript", "study_material", "pdf"])
                        self.progress_reporter.start_processing(task["name"], steps, prefix_for_progress)

                        if not task["transcript_file"].exists():
                            sys.stdout.write("\r" + " " * 120 + "\r")
                            self.status_reporter.info(f"{prefix_for_progress}Processing images: {task['stem']}/ ({len(task['image_files'])} images)")
                            img_res = self.image_processor.process(task["image_files"], task["transcript_file"])
                            if not img_res.success:
                                self.status_reporter.error(f"Failed to process images for {task['stem']}: {img_res.message}")
                                self.progress_reporter.complete_processing(False)
                                error_count[0] += 1
                                return
                        else:
                            self.progress_reporter.next_step(skipped=True)

                        result = self.process_single_source(task["transcript_file"], "images")
                        self.progress_reporter.complete_processing(result.success)

                        if result.success:
                            processed_count[0] += 1
                            processed_stems.add(task["stem"])
                            self.processed_stems.add(task["stem"])
                        else:
                            error_count[0] += 1
                            self.status_reporter.error(f"Failed to process study material for {task['stem']}: {result.message}")

                    elif task["type"] == "loose_images":
                        steps = PROCESSING_STEPS.get("image", ["transcript", "study_material", "pdf"])
                        self.progress_reporter.start_processing(task["name"], steps, prefix_for_progress)

                        if not task["transcript_file"].exists():
                            sys.stdout.write("\r" + " " * 120 + "\r")
                            self.status_reporter.info(f"{prefix_for_progress}Processing loose images: {task['folder_name']}/ ({len(task['images'])} images)")
                            img_res = self.image_processor.process(task["images"], task["transcript_file"])
                            if not img_res.success:
                                self.status_reporter.error(f"Failed to process loose images for {task['folder_name']}: {img_res.message}")
                                self.progress_reporter.complete_processing(False)
                                error_count[0] += 1
                                return
                        else:
                            self.progress_reporter.next_step(skipped=True)

                        result = self.process_single_source(task["transcript_file"], "images")
                        self.progress_reporter.complete_processing(result.success)

                        if result.success:
                            processed_count[0] += 1
                        else:
                            error_count[0] += 1
                            self.status_reporter.error(f"Failed to process study material for loose images in {task['folder_name']}: {result.message}")
                except Exception as e:
                    self.progress_reporter.complete_processing(False)
                    self.status_reporter.error(f"Error processing {task['name']}: {e}")
                    error_count[0] += 1

            def traverse_tree(current_tree, prefix=""):
                def sort_key(k):
                    is_task = k.startswith("__task__")
                    return (1 if is_task else 0, k.lower())

                keys = sorted(current_tree.keys(), key=sort_key)

                for i, key in enumerate(keys):
                    is_last = (i == len(keys) - 1)
                    connector = "└── " if is_last else "├── "
                    child_prefix = prefix + ("    " if is_last else "│   ")

                    node = current_tree[key]
                    if isinstance(node, dict) and not key.startswith("__task__"):
                        sys.stdout.write("\r" + " " * 120 + "\r")
                        print(f"{prefix}{connector}📁 {key}/")
                        traverse_tree(node, child_prefix)
                    else:
                        execute_task(node, prefix + connector)

            traverse_tree(tree, "")

            message = f"Processed {processed_count[0]} items successfully"
            if error_count[0] > 0:
                message += f" with {error_count[0]} errors"

            return ProcessResult(
                success=error_count[0] == 0,
                message=message,
                metadata={
                    "directory": str(directory),
                    "groups_processed": processed_count[0],
                    "errors": error_count[0]
                }
            )

        except Exception as e:
            raise VideoTranscriptionError(f"Failed to process directory {directory}: {e}")

    def _process_media_groups(self, file_groups: Dict[str, List[Path]], directory: Path) -> int:
        """Process video/audio/text groups with priority handling."""
        processed_count = 0

        for group_key in sorted(file_groups.keys(), key=lambda k: k.lower()):
            files = file_groups[group_key]

            # Find primary source (video > audio > text)
            source_path, start_type = self.file_discovery.find_primary_source(files)

            if source_path and start_type in ["video", "audio", "text"]:
                try:
                    # Get processing steps for this file type
                    steps = PROCESSING_STEPS.get(start_type, ["transcript", "study_material", "pdf"])

                    # Start progress display for this file
                    self.progress_reporter.start_processing(source_path.name, steps)

                    result = self.process_single_source(source_path, start_type)

                    # Complete progress display
                    self.progress_reporter.complete_processing(result.success)

                    # Move to next line for next file
                    if result.success:
                        processed_count += 1
                        # Extract stem for tracking
                        stem = source_path.stem
                        self.processed_stems.add(stem)
                    else:
                        self.status_reporter.error(f"Failed to process {source_path.name}: {result.message}")

                except Exception as e:
                    # Make sure to complete progress display on error
                    self.progress_reporter.complete_processing(False)
                    self.status_reporter.error(f"Error processing {source_path.name}: {e}")

        return processed_count

    def _process_image_groups(self, file_groups: Dict[str, List[Path]], directory: Path) -> int:
        """Process image groups, including those sharing stems with processed media."""
        processed_count = 0

        for group_key in sorted(file_groups.keys(), key=lambda k: k.lower()):
            files = file_groups[group_key]
            image_files = self.file_discovery.separate_image_files(files)

            if not image_files:
                continue

            # Determine transcript filename
            stem = group_key.split("::")[-1] if "::" in group_key else group_key

            # Use the unified transcript file; ImageProcessor will append if it exists
            # Ensure it generates in the exact directory of the image files (resolves subtree bug)
            target_dir = image_files[0].parent
            transcript_file = target_dir / f"{stem}.txt"

            try:
                # Get processing steps for this file type
                steps = PROCESSING_STEPS.get("image", ["transcript", "study_material", "pdf"])

                # Start progress display for this file
                self.progress_reporter.start_processing(transcript_file.name, steps)

                # Process images to transcript
                if not transcript_file.exists():
                    self.status_reporter.info(f"Processing images: {stem}/ ({len(image_files)} images)")
                    result = self.image_processor.process(image_files, transcript_file)

                    if not result.success:
                        self.status_reporter.error(f"Failed to process images for {stem}: {result.message}")
                        self.progress_reporter.complete_processing(False)
                        continue
                else:
                    self.progress_reporter.next_step(skipped=True)

                # Process transcript to study material
                result = self.process_single_source(transcript_file, "images")

                # Complete progress display
                self.progress_reporter.complete_processing(result.success)

                if result.success:
                    processed_count += 1
                    self.processed_stems.add(stem)
                else:
                    self.status_reporter.error(f"Failed to process study material for {stem}: {result.message}")

            except Exception as e:
                self.progress_reporter.complete_processing(False)
                self.status_reporter.error(f"Error processing images for {stem}: {e}")

        return processed_count

    def _process_loose_images(self, directory: Path) -> int:
        """Process remaining loose images that don't match any stem group."""
        # Find all image files
        all_files = self.file_discovery.discover_files(directory)
        all_image_files = [f for f in all_files if self.config.is_image_file(f)]

        # Filter out already processed images
        unprocessed_images = [
            f for f in all_image_files
            if f.stem not in self.processed_stems
        ]

        if not unprocessed_images:
            return 0

        # Group by directory
        dir_groups = {}
        for img_path in unprocessed_images:
            dir_groups.setdefault(img_path.parent, []).append(img_path)

        processed_count = 0

        for dir_path, images in dir_groups.items():
            folder_name = dir_path.name
            transcript_file = dir_path / f"{folder_name}.txt"

            try:
                # Get processing steps for this file type
                steps = PROCESSING_STEPS.get("image", ["transcript", "study_material", "pdf"])

                # Start progress display for this file
                self.progress_reporter.start_processing(transcript_file.name, steps)

                # Process images to transcript
                if not transcript_file.exists():
                    self.status_reporter.info(f"Processing loose images: {folder_name}/ ({len(images)} images)")
                    result = self.image_processor.process(images, transcript_file)

                    if not result.success:
                        self.status_reporter.error(f"Failed to process loose images in {folder_name}: {result.message}")
                        self.progress_reporter.complete_processing(False)
                        continue
                else:
                    self.progress_reporter.next_step(skipped=True)

                # Process transcript to study material
                result = self.process_single_source(transcript_file, "images")

                # Complete progress display
                self.progress_reporter.complete_processing(result.success)

                if result.success:
                    processed_count += 1
                else:
                    self.status_reporter.error(f"Failed to process study material for loose images in {folder_name}: {result.message}")

            except Exception as e:
                self.progress_reporter.complete_processing(False)
                self.status_reporter.error(f"Error processing loose images in {folder_name}: {e}")

        return processed_count

    def process_single_source(self, source_path: Path, start_type: str) -> ProcessResult:
        """Process a single source file through the complete pipeline."""
        try:
            # Generate output paths
            paths = self.file_discovery.get_output_paths(source_path, start_type)

            # Step 1: Extract audio (if starting from video)
            if start_type == "video":
                if not paths["audio_file"].exists():
                    result = self.audio_processor.extract_audio_from_video(source_path, paths["audio_file"])

                    if not result.success:
                        return result
                    self.progress_reporter.next_step()
                else:
                    self.status_reporter.info(f"Audio file already exists: {paths['audio_file'].name}")
                    self.progress_reporter.next_step(skipped=True)

            # EARLY EXIT: target == "audio"
            if self.config.target == "audio":
                return ProcessResult(
                    success=True,
                    output_path=paths["audio_file"] if start_type == "video" else source_path,
                    message=f"Reached target 'audio' for {source_path.name}",
                    metadata={"source_type": start_type, "target_reached": "audio"}
                )

            # Step 2: Transcribe (if we have audio but no transcript)
            if not paths["transcript_file"].exists():
                if start_type in ["video", "audio"] or paths["audio_file"].exists():
                    # Use audio file for transcription
                    audio_source = paths["audio_file"] if start_type == "video" else source_path

                    result = self.audio_processor.process(audio_source, paths["transcript_file"])

                    if not result.success:
                        return result
                else:
                    # For text or images, source is already the transcript
                    result = self.text_processor.process(source_path, paths["transcript_file"])

                    if not result.success:
                        return result

                # Move to next step
                self.progress_reporter.next_step()
            else:
                if start_type in ["video", "audio"]:
                    self.progress_reporter.next_step(skipped=True)

            # EARLY EXIT: target == "text"
            if self.config.target == "text":
                return ProcessResult(
                    success=True,
                    output_path=paths["transcript_file"],
                    message=f"Reached target 'text' for {source_path.name}",
                    metadata={"source_type": start_type, "target_reached": "text"}
                )

            # Step 3: Generate study material
            if not paths["study_file"].exists():
                result = self.study_generator.generate(paths["transcript_file"])

                if not result.success:
                    return result

                # Move to next step
                self.progress_reporter.next_step()
            else:
                self.progress_reporter.next_step(skipped=True)

            # EARLY EXIT: target == "markdown"
            if self.config.target == "markdown":
                return ProcessResult(
                    success=True,
                    output_path=paths["study_file"],
                    message=f"Reached target 'markdown' (study material) for {source_path.name}",
                    metadata={"source_type": start_type, "target_reached": "markdown"}
                )

            # Step 4: Generate PDF (if requested and not already present)
            if self.config.generate_pdf:
                if not paths["pdf_file"].exists():
                    # PDF is missing — generate it from the existing study markdown
                    pdf_result = self.study_generator.generate_pdf_only(
                        paths["transcript_file"], paths["study_file"], paths["pdf_file"]
                    )
                    if not pdf_result.success:
                        self.status_reporter.error(
                            f"PDF generation failed for {source_path.name}: {pdf_result.message}"
                        )
                    self.progress_reporter.next_step()
                else:
                    self.progress_reporter.next_step(skipped=True)

            return ProcessResult(
                success=True,
                output_path=paths["study_file"],
                message=f"Successfully processed {source_path.name}",
                metadata={
                    "source_type": start_type,
                    "output_paths": {k: str(v) for k, v in paths.items()}
                }
            )

        except Exception as e:
            raise ProcessingError(
                f"Failed to process {source_path.name}: {e}",
                processor="VideoTranscriptionPipeline",
                file_path=str(source_path)
            )

    def validate_prerequisites(self) -> Dict[str, bool]:
        """Validate that all prerequisites are met."""
        validation = {}

        # Check Whisper availability without loading the model
        try:
            import whisper
            validation["whisper_model"] = True
        except ImportError:
            validation["whisper_model"] = False

        # Check study generator prerequisites
        study_validation = self.study_generator.validate_prerequisites()
        validation.update(study_validation)

        # Compute overall readiness
        validation["overall_ready"] = all(validation.values())

        return validation

    def get_pipeline_info(self) -> Dict[str, any]:
        """Get information about the pipeline configuration and status."""
        return {
            "config": {
                "whisper_model": self.config.whisper_model,
                "llm_model": self.config.llm_model,
                "generate_pdf": self.config.generate_pdf,
                "verbose": self.config.verbose
            },
            "components": {
                "whisper_loaded": self.whisper_model is not None,
                "study_generator_info": self.study_generator.get_generator_info()
            },
            "processed_stems": len(self.processed_stems)
        }

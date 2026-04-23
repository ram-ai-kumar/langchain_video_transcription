"""Main pipeline orchestrator for video transcription and study material generation."""

import logging
import os
import re
import signal
import sys
import whisper
import torch
from pathlib import Path
from typing import Dict, List, Optional, Set

from src.core.config import PipelineConfig
from src.core.exceptions import VideoTranscriptionError, ProcessingError
from src.generators.study_generator import StudyMaterialGenerator
from src.processors.audio_processor import AudioProcessor
from src.processors.image_processor import ImageProcessor
from src.processors.text_processor import TextProcessor
from src.processors.base import ProcessResult
from src.utils.file_utils import FileDiscovery, FileManager
from src.utils.ui_utils import StatusReporter
from src.utils.media_utils import MediaTypeDetector, MediaProcessorFactory
from src.utils.progress_tracker import ProgressTracker


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

    # Add console handler (use stderr to avoid interfering with Rich progress display)
    console_handler = logging.StreamHandler(sys.stderr)
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

        # Initialize processors
        self.audio_processor = AudioProcessor(config)
        self.image_processor = ImageProcessor(config)
        self.text_processor = TextProcessor(config)

        # Media type detection
        self.media_detector = MediaTypeDetector(config)

        # Track processed items
        self.processed_stems: Set[str] = set()

        # Progress tracking
        self.progress_tracker = ProgressTracker()

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

            # Process files sequentially using existing helper methods
            try:
                media_count = self._process_media_groups(file_groups, directory)
                image_count = self._process_image_groups(file_groups, directory)
                loose_count = self._process_loose_images(directory)
            except KeyboardInterrupt:
                print("\n\n🛑 Processing interrupted by user (Ctrl+C). Terminating...")
                os._exit(130)

            total_processed = media_count + image_count + loose_count
            total_errors = (len(file_groups) - media_count) + (len(file_groups) - image_count) + loose_count

            message = f"Processed {total_processed} items successfully"
            if total_errors > 0:
                message += f" with {total_errors} errors"

            return ProcessResult(
                success=total_errors == 0,
                message=message,
                metadata={
                    "directory": str(directory),
                    "groups_processed": total_processed,
                    "errors": total_errors
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
                    result = self.process_single_source(source_path, start_type)

                    if result.success:
                        processed_count += 1
                        # Extract stem for tracking
                        stem = source_path.stem
                        self.processed_stems.add(stem)
                    else:
                        self.status_reporter.error(f"Failed to process {source_path.name}: {result.message}")

                except Exception as e:
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
                # Process images to transcript
                if not transcript_file.exists():
                    self.status_reporter.info(f"Processing images: {stem}/ ({len(image_files)} images)")
                    result = self.image_processor.process(image_files, transcript_file)

                    if not result.success:
                        self.status_reporter.error(f"Failed to process images for {stem}: {result.message}")
                        continue

                # Process transcript to study material
                result = self.process_single_source(transcript_file, "images")

                if result.success:
                    processed_count += 1
                    self.processed_stems.add(stem)
                else:
                    self.status_reporter.error(f"Failed to process study material for {stem}: {result.message}")

            except Exception as e:
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
                # Process images to transcript
                if not transcript_file.exists():
                    self.status_reporter.info(f"Processing loose images: {folder_name}/ ({len(images)} images)")
                    result = self.image_processor.process(images, transcript_file)

                    if not result.success:
                        self.status_reporter.error(f"Failed to process loose images in {folder_name}: {result.message}")
                        continue

                # Process transcript to study material
                result = self.process_single_source(transcript_file, "images")

                if result.success:
                    processed_count += 1
                else:
                    self.status_reporter.error(f"Failed to process study material for loose images in {folder_name}: {result.message}")

            except Exception as e:
                self.status_reporter.error(f"Error processing loose images in {folder_name}: {e}")

        return processed_count

    def _migrate_legacy_unsanitized_files(self, source_path: Path, paths: dict) -> None:
        """Rename legacy output files that have \u202f (or other Unicode whitespace) in their
        stems to the corresponding sanitized (regular-space) versions.

        This handles directories that were processed by an older version of the pipeline
        that wrote output filenames verbatim from the source stem.  Without this step the
        existence-checks further down would see a missing sanitized file, regenerate it,
        and leave *two* copies (old unsanitized + new sanitized) on disk.
        """
        original_stem = source_path.stem
        sanitized_stem = re.sub(r'\s', ' ', original_stem)
        if original_stem == sanitized_stem:
            return  # nothing to migrate

        dir_path = source_path.parent
        legacy_map = {
            "audio_file":      dir_path / f"{original_stem}.mp3",
            "transcript_file": dir_path / f"{original_stem}.txt",
            "study_file":      dir_path / f"{original_stem}.md",
            "pdf_file":        dir_path / f"{original_stem}.pdf",
        }

        for key, legacy_path in legacy_map.items():
            sanitized_path = paths.get(key)
            if (
                sanitized_path
                and legacy_path != sanitized_path
                and legacy_path.exists()
                and not sanitized_path.exists()
            ):
                legacy_path.rename(sanitized_path)
                self.logger.info("Renamed legacy file: %s -> %s", legacy_path.name, sanitized_path.name)

    def _migrate_legacy_study_files(self, source_path: Path, paths: dict) -> None:
        """Rename legacy study files that have _study.md suffix to .md.

        This handles directories that were processed by an older version of the pipeline
        that used _study.md suffix for study material files.
        """
        dir_path = source_path.parent
        base = re.sub(r'\s', ' ', source_path.stem)

        legacy_study_file = dir_path / f"{base}_study.md"
        new_study_file = paths.get("study_file")

        if (
            new_study_file
            and legacy_study_file != new_study_file
            and legacy_study_file.exists()
            and not new_study_file.exists()
        ):
            legacy_study_file.rename(new_study_file)
            self.logger.info("Renamed legacy study file: %s -> %s", legacy_study_file.name, new_study_file.name)

    def _get_processing_stages(self, start_type: str) -> list[str]:
        """Get the list of processing stages for a given start type."""
        stages = []

        if start_type == "video":
            stages.append("audio")

        if start_type in ["video", "audio", "text"]:
            stages.append("text")
        else:
            # For images, text comes from OCR
            stages.append("text")

        # Study material generation
        if self.config.target in ["markdown", "pdf"] or self.config.target == "study":
            stages.append("markdown")

        # PDF generation
        if self.config.generate_pdf and self.config.target != "markdown":
            stages.append("pdf")

        return stages

    def process_single_source(self, source_path: Path, start_type: str, task_name: Optional[str] = None) -> ProcessResult:
        """Process a single source file through the complete pipeline."""
        t_name = task_name or source_path.name
        try:
            # Generate output paths
            paths = self.file_discovery.get_output_paths(source_path, start_type)

            # Rename any legacy files that have Unicode whitespace in their stems so that
            # the existence-checks below see them correctly and skip regeneration.
            self._migrate_legacy_unsanitized_files(source_path, paths)

            # Rename any legacy study files that have _study.md suffix to .md
            self._migrate_legacy_study_files(source_path, paths)

            # Start progress tracking
            stages = self._get_processing_stages(start_type)
            self.progress_tracker.start_file(source_path, stages)
            current_stage = 0

            # Step 1: Extract audio (if starting from video)
            if start_type == "video":
                if not paths["audio_file"].exists():
                    result = self.audio_processor.extract_audio_from_video(source_path, paths["audio_file"])
                    if not result.success:
                        self.progress_tracker.complete_file(source_path)
                        return result
                else:
                    self.status_reporter.info(f"Audio file already exists: {paths['audio_file'].name}")

                # Complete audio stage
                self.progress_tracker.complete_stage(source_path)
                current_stage += 1

            # EARLY EXIT: target == "audio"
            if self.config.target == "audio":
                self.progress_tracker.complete_file(source_path)
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
                        self.progress_tracker.complete_file(source_path)
                        return result
                else:
                    # For text or images, source is already the transcript
                    result = self.text_processor.process(source_path, paths["transcript_file"])
                    if not result.success:
                        self.progress_tracker.complete_file(source_path)
                        return result

            # Complete text stage
            self.progress_tracker.complete_stage(source_path)
            current_stage += 1

            # EARLY EXIT: target == "text"
            if self.config.target == "text":
                self.progress_tracker.complete_file(source_path)
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
                    self.progress_tracker.complete_file(source_path)
                    return result

            # Complete markdown stage
            self.progress_tracker.complete_stage(source_path)
            current_stage += 1

            # EARLY EXIT: target == "markdown"
            if self.config.target == "markdown":
                self.progress_tracker.complete_file(source_path)
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

                # Complete PDF stage
                self.progress_tracker.complete_stage(source_path)
                current_stage += 1

            # Complete file processing
            self.progress_tracker.complete_file(source_path)

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
            # Complete file tracking on error
            self.progress_tracker.complete_file(source_path)
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

"""Main pipeline orchestrator for video transcription and study material generation."""

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


class VideoTranscriptionPipeline:
    """Main pipeline coordinator that manages the entire processing workflow."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.whisper_model: Optional[whisper.Whisper] = None

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
                device = "cuda" if torch.cuda.is_available() else "cpu"
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

            # Get all file groups
            file_groups = self.file_discovery.group_files_by_stem(directory)

            if not file_groups:
                return ProcessResult(
                    success=True,
                    message="No supported files found in directory",
                    metadata={"directory": str(directory), "groups_found": 0}
                )

            self.status_reporter.info(f"Found {len(file_groups)} file groups to process")

            # Process in three passes
            processed_count = 0
            error_count = 0

            # Pass 1: Process video/audio/text groups
            processed_count += self._process_media_groups(file_groups, directory)

            # Pass 2: Process image groups
            processed_count += self._process_image_groups(file_groups, directory)

            # Pass 3: Process loose images
            processed_count += self._process_loose_images(directory)

            message = f"Processed {processed_count} items successfully"
            if error_count > 0:
                message += f" with {error_count} errors"

            return ProcessResult(
                success=error_count == 0,
                message=message,
                metadata={
                    "directory": str(directory),
                    "groups_processed": processed_count,
                    "errors": error_count
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

            if stem in self.processed_stems:
                transcript_file = directory / f"{stem}_images.txt"
            else:
                transcript_file = directory / f"{stem}.txt"

            try:
                # Process images to transcript
                if not transcript_file.exists():
                    self.status_reporter.info(f"Processing images: {stem}/ ({len(image_files)} images)")

                    if self.config.show_spinner:
                        result = Spinner(
                            f"    images ({len(image_files)}) > transcript ..."
                        )(self.image_processor.process, image_files, transcript_file)
                    else:
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
            transcript_file = dir_path / f"{folder_name}_images.txt"

            try:
                # Process images to transcript
                if not transcript_file.exists():
                    self.status_reporter.info(f"Processing loose images: {folder_name}/ ({len(images)} images)")

                    if self.config.show_spinner:
                        result = Spinner(
                            f"    images ({len(images)}) > transcript ..."
                        )(self.image_processor.process, images, transcript_file)
                    else:
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
                else:
                    self.status_reporter.info(f"Audio file already exists: {paths['audio_file'].name}")

                # Move to next step
                self.progress_reporter.next_step()

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
                    self.progress_reporter.next_step()

            # Step 3: Generate study material
            if not paths["study_file"].exists():
                result = self.study_generator.generate(paths["transcript_file"])

                if not result.success:
                    return result

                # Move to next step
                self.progress_reporter.next_step()
            else:
                self.progress_reporter.next_step()

            # Step 4: Generate PDF (if requested and not already present)
            if self.config.generate_pdf:
                if not paths["pdf_file"].exists():
                    # PDF is missing — generate it from the existing study markdown
                    self.status_reporter.info(f"Generating PDF for {source_path.name}...")
                    pdf_result = self.study_generator.generate_pdf_only(
                        paths["transcript_file"], paths["study_file"], paths["pdf_file"]
                    )
                    if pdf_result.success:
                        self.status_reporter.info(f"PDF generated: {paths['pdf_file'].name}")
                    else:
                        self.status_reporter.error(
                            f"PDF generation failed for {source_path.name}: {pdf_result.message}"
                        )
                else:
                    self.status_reporter.info(f"PDF already exists: {paths['pdf_file'].name}")
                self.progress_reporter.next_step()

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

        # Check Whisper model availability
        try:
            self._load_whisper_model()
            validation["whisper_model"] = True
        except Exception:
            validation["whisper_model"] = False

        # Check study generator prerequisites
        study_validation = self.study_generator.validate_prerequisites()
        validation.update(study_validation)

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

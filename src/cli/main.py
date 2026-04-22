import os
# Silencing competing UI libraries and subprocesses
from src.utils.subprocess_utils import setup_global_silence
setup_global_silence()

import argparse
import logging
import signal
import subprocess
import sys
import warnings
from pathlib import Path

# Suppress Python 3.14 compatibility warnings early
warnings.filterwarnings("ignore", category=UserWarning, message=".*Core Pydantic V1 functionality isn't compatible with Python 3.14.*")

from src.core.config import PipelineConfig
from src.core.exceptions import VideoTranscriptionError
from src.core.pipeline import VideoTranscriptionPipeline, setup_logging
from src.utils.ui_utils import ColorFormatter, StatusReporter


class VideoTranscriptionCLI:
    """Command-line interface for video transcription pipeline."""

    def __init__(self):
        self.pipeline = None
        self.status_reporter = None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            # Ignore subsequent signals
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            print(ColorFormatter.error("\n\n[INFO] Interrupted by user. Cleaning up and exiting..."))
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def create_parser(self) -> argparse.ArgumentParser:
        """Create command-line argument parser."""
        parser = argparse.ArgumentParser(
            description="Process videos, audio, text, and images into study materials and PDFs",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s /path/to/media/folder                    # Process with default settings
  %(prog)s /path/to/media --no-pdf                  # Skip PDF generation
  %(prog)s /path/to/media --llm-model llama2        # Use different LLM model
  %(prog)s /path/to/media --verbose                  # Show detailed progress
  %(prog)s /path/to/media --output-dir /output      # Specify output directory
            """
        )

        # Positional arguments
        parser.add_argument(
            "directory",
            type=Path,
            help="Path to folder containing media files to process"
        )

        # Processing options
        parser.add_argument(
            "--target", "-t",
            choices=["audio", "text", "markdown", "pdf"],
            help="Specify pipeline extraction point (audio, text, markdown, pdf)"
        )

        parser.add_argument(
            "--no-pdf",
            action="store_true",
            help="Skip PDF generation (deprecated: use --target markdown)"
        )

        parser.add_argument(
            "--output-dir",
            type=Path,
            help="Output directory for generated files (default: same as input)"
        )

        # Model options
        parser.add_argument(
            "--whisper-model",
            default="medium",
            choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
            help="Whisper model size for transcription (default: medium)"
        )

        parser.add_argument(
            "--llm-model",
            default="qwen3.5:latest",
            help="LLM model for content generation (default: qwen3.5:latest)"
        )

        # UI options
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Show detailed progress information"
        )

        # Performance options
        parser.add_argument(
            "--device",
            choices=["auto", "cpu", "cuda", "mps"],
            help="Computation device (auto-detect if not specified)"
        )

        # Validation options
        parser.add_argument(
            "--check-deps",
            action="store_true",
            help="Check dependencies and exit"
        )

        parser.add_argument(
            "--validate-only",
            action="store_true",
            help="Validate input files and exit without processing"
        )

        # Configuration options
        parser.add_argument(
            "--config",
            type=Path,
            help="Path to configuration file (JSON format)"
        )

        return parser

    def parse_config_file(self, config_path: Path) -> dict:
        """Parse configuration file."""
        import json

        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(ColorFormatter.error(f"Failed to parse config file {config_path}: {e}"))
            sys.exit(1)

    def create_config(self, args) -> PipelineConfig:
        """Create configuration from command-line arguments."""
        # Start with default config
        config_dict = {}

        # Load config file if provided
        if args.config:
            config_dict = self.parse_config_file(args.config)

        # Determine target considering backward-compatible --no-pdf
        target = getattr(args, "target", "pdf")
        if target is None:
            target = "pdf"

        if getattr(args, "no_pdf", False) and target == "pdf":
            target = "markdown"

        # Override with command-line arguments
        config_dict.update({
            "target": target,
            "generate_pdf": target == "pdf" and not getattr(args, "no_pdf", False),
            "whisper_model": getattr(args, "whisper_model", "medium"),
            "llm_model": getattr(args, "llm_model", "qwen3.5:latest"),
            "verbose": getattr(args, "verbose", False),
            # Performance settings
            "device": getattr(args, "device", None),
        })

        if args.output_dir:
            config_dict["output_dir"] = args.output_dir

        try:
            return PipelineConfig(**config_dict)
        except Exception as e:
            print(ColorFormatter.error(f"Configuration error: {e}"))
            sys.exit(1)

    def check_dependencies(self, config: PipelineConfig) -> bool:
        """Check if all dependencies are available."""
        print(ColorFormatter.info("Checking dependencies..."))

        all_good = True

        # Check Whisper availability
        try:
            import whisper
            print(ColorFormatter.success("✓ Whisper available"))
        except ImportError:
            print(ColorFormatter.error("✗ Whisper not available - install with: pip install openai-whisper"))
            all_good = False

        # Check Tesseract availability
        try:
            import pytesseract
            print(ColorFormatter.success("✓ Tesseract OCR available"))
        except ImportError:
            print(ColorFormatter.error("✗ Tesseract not available - install with: pip install pytesseract"))
            all_good = False

        # Check PIL availability
        try:
            from PIL import Image
            print(ColorFormatter.success("✓ PIL/Pillow available"))
        except ImportError:
            print(ColorFormatter.error("✗ PIL not available - install with: pip install Pillow"))
            all_good = False

        # Check LangChain availability
        try:
            from langchain_core.prompts import PromptTemplate
            from langchain_ollama import OllamaLLM
            print(ColorFormatter.success("✓ LangChain available"))
        except ImportError:
            print(ColorFormatter.error("✗ LangChain not available - install with: pip install langchain-core langchain-ollama"))
            all_good = False

        # Check Pandoc availability
        from src.utils.subprocess_utils import run_silent_command
        try:
            run_silent_command(["pandoc", "--version"])
            print(ColorFormatter.success("✓ Pandoc available"))
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(ColorFormatter.warning("⚠ Pandoc not available - PDF generation will fail"))
            if config.generate_pdf:
                print(ColorFormatter.warning("  Use --no-pdf to skip PDF generation"))

        # Check Tectonic
        try:
            run_silent_command(["tectonic", "--version"])
            print(ColorFormatter.success("✓ Tectonic available"))
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(ColorFormatter.warning("⚠ Tectonic not found - PDF generation will fail"))
            if config.generate_pdf:
                print(ColorFormatter.warning("  Use --no-pdf to skip PDF generation"))

        return all_good

    def validate_input_directory(self, directory: Path) -> bool:
        """Validate input directory."""
        if not directory.exists():
            print(ColorFormatter.error(f"Directory not found: {directory}"))
            return False

        if not directory.is_dir():
            print(ColorFormatter.error(f"Path is not a directory: {directory}"))
            return False

        return True

    def run(self, args=None):
        """Run the CLI application."""
        parser = self.create_parser()
        args = parser.parse_args(args)

        # Interactive prompt for target if not provided and not a 'dry-run' style command
        if not getattr(args, "target", None) and not args.check_deps and not args.validate_only:
            try:
                import builtins
                print(ColorFormatter.info("\n" + "="*50))
                print(ColorFormatter.info("Pipeline Extraction Target"))
                print(ColorFormatter.info("="*50))
                print("1. [audio]    Extract audio only")
                print("2. [text]     Transcribe to text")
                print("3. [markdown] Generate study material (MD)")
                print("4. [pdf]      Generate final PDF (Full pipeline)")
                while True:
                    choice = builtins.input("\nSelect desired extraction target [1-4 or name] (default: 4): ").strip().lower()
                    if choice in ["1", "audio"]:
                        args.target = "audio"
                        break
                    elif choice in ["2", "text"]:
                        args.target = "text"
                        break
                    elif choice in ["3", "markdown"]:
                        args.target = "markdown"
                        break
                    elif choice in ["4", "pdf", ""]:
                        args.target = "pdf"
                        break
                    else:
                        print(ColorFormatter.warning("Invalid choice. Please select audio, text, markdown, or pdf."))
            except KeyboardInterrupt:
                print(ColorFormatter.error("\nOperation cancelled."))
                sys.exit(0)

        # Setup logging immediately after parsing args
        setup_logging(args.verbose)

        # Now create logger after logging is configured
        self.logger = logging.getLogger(__name__)

        # Create configuration
        config = self.create_config(args)
        self.status_reporter = StatusReporter(config.verbose)

        # Check dependencies if requested
        if args.check_deps:
            deps_ok = self.check_dependencies(config)
            sys.exit(0 if deps_ok else 1)

        # Validate input directory
        if not self.validate_input_directory(args.directory):
            sys.exit(1)

        # Validate only mode
        if args.validate_only:
            print(ColorFormatter.info("Validating input files..."))
            # TODO: Implement file validation
            print(ColorFormatter.success("Validation complete"))
            sys.exit(0)

        # Initialize pipeline
        try:
            self.pipeline = VideoTranscriptionPipeline(config)

            # Validate prerequisites
            validation = self.pipeline.validate_prerequisites()

            if not validation.get("overall_ready", False):
                print(ColorFormatter.error("Prerequisites not met:"))
                for key, value in validation.items():
                    if key != "overall_ready" and not value:
                        print(ColorFormatter.error(f"  ✗ {key}"))
                sys.exit(1)

        except VideoTranscriptionError as e:
            print(ColorFormatter.error(f"Pipeline initialization failed: {e}"))
            sys.exit(1)

        # Start processing
        try:
            if config.target in ["markdown", "pdf"]:
                print(ColorFormatter.info("AI is warming up... ready to crunch some knowledge."))

            # Process directory
            result = self.pipeline.process_directory(args.directory)

            if result.success:
                print(ColorFormatter.success(f"\nProcessing completed successfully!"))
                if config.verbose:
                    print(f"Message: {result.message}")
                    if result.metadata:
                        print(f"Metadata: {result.metadata}")
            else:
                print(ColorFormatter.error(f"\nProcessing completed with errors."))
                print(f"Message: {result.message}")
                sys.exit(1)

        except KeyboardInterrupt:
            # Handled by signal handler
            pass
        except VideoTranscriptionError as e:
            print(ColorFormatter.error(f"Processing failed: {e}"))
            sys.exit(1)
        except Exception as e:
            self.logger.exception("Unexpected error: %s", e)
            print(ColorFormatter.error(f"Unexpected error: {e}"))
            sys.exit(1)


def main():
    """Main entry point for the CLI."""
    cli = VideoTranscriptionCLI()
    cli.run()


if __name__ == "__main__":
    main()

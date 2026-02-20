"""Study material generator that coordinates the generation process."""

from pathlib import Path

from src.core.config import PipelineConfig
from src.core.exceptions import ProcessingError
from src.generators.pdf_generator import PDFGenerator
from src.processors.llm_processor import LLMProcessor
from src.processors.base import ProcessResult


class StudyMaterialGenerator:
    """Coordinates study material generation process."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.llm_processor = LLMProcessor(config)
        self.pdf_generator = PDFGenerator(config) if config.generate_pdf else None
    
    def generate(self, transcript_path: Path, output_dir: Path = None) -> ProcessResult:
        """Generate complete study material from transcript."""
        try:
            # Determine output directory
            if output_dir is None:
                output_dir = transcript_path.parent
            
            # Generate output paths
            base_name = transcript_path.stem
            study_file = output_dir / f"{base_name}_study.md"
            pdf_file = output_dir / f"{base_name}.pdf"
            
            # Generate study material using LLM
            llm_result = self.llm_processor.process(transcript_path, study_file)
            
            if not llm_result.success:
                return ProcessResult(
                    success=False,
                    message=f"Failed to generate study material: {llm_result.message}",
                    metadata=llm_result.metadata
                )
            
            # Generate PDF if requested
            pdf_result = None
            if self.pdf_generator and self.config.generate_pdf:
                try:
                    pdf_result = self.pdf_generator.generate_pdf(study_file, pdf_file)
                except Exception as e:
                    # Log PDF generation error but don't fail the entire process
                    if self.config.verbose:
                        print(f"[WARN] PDF generation failed: {e}")
                    pdf_result = ProcessResult(
                        success=False,
                        message=f"PDF generation failed: {e}",
                        output_path=pdf_file
                    )
            
            # Prepare final result
            success = llm_result.success and (pdf_result is None or pdf_result.success)
            
            if success:
                message = f"Successfully generated study material"
                if pdf_result and pdf_result.success:
                    message += " and PDF"
            else:
                message = "Study material generated with issues"
            
            metadata = {
                "study_file": str(study_file),
                "pdf_file": str(pdf_file) if pdf_result else None,
                "llm_metadata": llm_result.metadata,
                "pdf_metadata": pdf_result.metadata if pdf_result else None
            }
            
            return ProcessResult(
                success=success,
                output_path=study_file,
                message=message,
                metadata=metadata
            )
            
        except Exception as e:
            raise ProcessingError(
                f"Failed to generate study material from {transcript_path.name}: {e}",
                file_path=str(transcript_path),
                processor="StudyMaterialGenerator"
            )
    
    def validate_prerequisites(self) -> dict:
        """Validate that all prerequisites are met for study generation."""
        validation = {
            "llm_available": False,
            "pdf_available": False,
            "prompt_file_exists": False,
            "overall_ready": False
        }
        
        # Check LLM availability
        try:
            validation["llm_available"] = self.llm_processor.validate_llm_connection()
        except Exception:
            validation["llm_available"] = False
        
        # Check PDF generation availability
        if self.pdf_generator:
            validation["pdf_available"] = self.pdf_generator.validate_dependencies()
        else:
            validation["pdf_available"] = not self.config.generate_pdf  # Not needed if not generating PDF
        
        # Check prompt file
        validation["prompt_file_exists"] = self.config.prompt_file.exists()
        
        # Overall readiness
        validation["overall_ready"] = (
            validation["llm_available"] and 
            validation["prompt_file_exists"] and
            (validation["pdf_available"] or not self.config.generate_pdf)
        )
        
        return validation
    
    def get_generator_info(self) -> dict:
        """Get information about the generator configuration."""
        info = {
            "config": {
                "llm_model": self.config.llm_model,
                "generate_pdf": self.config.generate_pdf,
                "prompt_file": str(self.config.prompt_file)
            },
            "llm_info": self.llm_processor.get_model_info()
        }
        
        if self.pdf_generator:
            info["pdf_info"] = self.pdf_generator.get_dependency_info()
        
        return info

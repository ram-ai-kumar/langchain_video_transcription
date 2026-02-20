"""Image processor for OCR text extraction using Tesseract."""

from pathlib import Path
from typing import List

from PIL import Image
import pytesseract

from src.core.config import PipelineConfig
from src.core.exceptions import OCRProcessingError
from src.processors.base import BaseProcessor, ProcessResult


class ImageProcessor(BaseProcessor):
    """Handles OCR processing of images."""
    
    def __init__(self, config: PipelineConfig):
        super().__init__(config)
    
    def can_process(self, file_path: Path) -> bool:
        """Check if processor can handle the file type."""
        return self.config.is_image_file(file_path)
    
    def process(self, image_files: List[Path], output_path: Path) -> ProcessResult:
        """Extract text from multiple images and save to output file."""
        try:
            if not image_files:
                return ProcessResult(
                    success=False,
                    message="No image files provided for processing"
                )
            
            # Validate all input files
            for img_path in image_files:
                self.validate_input(img_path)
            
            self.ensure_output_dir(output_path)
            
            all_text = []
            processed_count = 0
            failed_count = 0
            
            for img_path in image_files:
                try:
                    # Open image and extract text
                    img = Image.open(img_path)
                    text = pytesseract.image_to_string(img, lang=self.config.ocr_language).strip()
                    
                    if text:
                        all_text.append(text)
                        processed_count += 1
                    else:
                        if self.config.verbose:
                            print(f"[WARN] No text found in {img_path.name}")
                    
                except Exception as e:
                    failed_count += 1
                    if self.config.verbose:
                        print(f"[WARN] Could not OCR {img_path.name}: {e}")
            
            # Combine all extracted text
            combined_text = "\n\n".join(all_text)
            
            # Write to output file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(combined_text)
            
            # Prepare result message
            if processed_count > 0:
                message = f"Successfully processed {processed_count} images"
                if failed_count > 0:
                    message += f" ({failed_count} failed)"
            else:
                message = "No text extracted from any images"
            
            return ProcessResult(
                success=processed_count > 0,
                output_path=output_path,
                message=message,
                metadata={
                    "total_images": len(image_files),
                    "processed_images": processed_count,
                    "failed_images": failed_count,
                    "text_length": len(combined_text)
                }
            )
            
        except Exception as e:
            raise OCRProcessingError(
                f"Failed to process images: {e}",
                processor="ImageProcessor"
            )
    
    def process_single_image(self, image_path: Path, output_path: Path) -> ProcessResult:
        """Extract text from a single image."""
        return self.process([image_path], output_path)

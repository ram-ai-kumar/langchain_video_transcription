"""LLM processor for generating study materials using LangChain and Ollama."""

from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from langchain_core.runnables import RunnableSequence

from src.core.config import PipelineConfig
from src.core.exceptions import LLMProcessingError
from src.processors.base import BaseProcessor, ProcessResult


class LLMProcessor(BaseProcessor):
    """Handles LLM-based content generation for study materials."""
    
    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        self.llm = None
        self.prompt_template = None
        self.study_chain = None
    
    def can_process(self, file_path: Path) -> bool:
        """Check if processor can handle the file type."""
        return self.config.is_text_file(file_path)
    
    def _load_llm(self) -> OllamaLLM:
        """Load the LLM model if not already loaded."""
        if self.llm is None:
            try:
                self.llm = OllamaLLM(model=self.config.llm_model)
            except Exception as e:
                raise LLMProcessingError(
                    f"Failed to load LLM model '{self.config.llm_model}': {e}",
                    processor="LLMProcessor"
                )
        return self.llm
    
    def _load_prompt_template(self) -> PromptTemplate:
        """Load the prompt template from file."""
        if self.prompt_template is None:
            try:
                with open(self.config.prompt_file, "r", encoding="utf-8") as f:
                    prompt_text = f.read()
                self.prompt_template = PromptTemplate.from_template(prompt_text)
            except Exception as e:
                raise LLMProcessingError(
                    f"Failed to load prompt template from {self.config.prompt_file}: {e}",
                    processor="LLMProcessor"
                )
        return self.prompt_template
    
    def _get_study_chain(self) -> RunnableSequence:
        """Get the study material generation chain."""
        if self.study_chain is None:
            llm = self._load_llm()
            prompt = self._load_prompt_template()
            self.study_chain = RunnableSequence(first=prompt, last=llm)
        return self.study_chain
    
    def process(self, transcript_path: Path, study_file_path: Path) -> ProcessResult:
        """Generate study material from transcript."""
        try:
            self.validate_input(transcript_path)
            self.ensure_output_dir(study_file_path)
            
            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript_text = f.read()
            
            if not transcript_text.strip():
                return ProcessResult(
                    success=False,
                    message=f"Transcript file is empty: {transcript_path.name}"
                )
            
            # Generate study material
            chain = self._get_study_chain()
            study_material = chain.invoke({"transcript": transcript_text})
            
            # Write study material to file
            with open(study_file_path, "w", encoding="utf-8") as f:
                f.write(study_material)
            
            return ProcessResult(
                success=True,
                output_path=study_file_path,
                message=f"Generated study material from {transcript_path.name}",
                metadata={
                    "transcript_length": len(transcript_text),
                    "study_material_length": len(study_material),
                    "llm_model": self.config.llm_model
                }
            )
            
        except Exception as e:
            raise LLMProcessingError(
                f"Failed to generate study material from {transcript_path.name}: {e}",
                file_path=str(transcript_path),
                processor="LLMProcessor"
            )
    
    def validate_llm_connection(self) -> bool:
        """Validate that the LLM is accessible and working."""
        try:
            llm = self._load_llm()
            # Simple test invocation
            response = llm.invoke("Test")
            return len(response) > 0
        except Exception:
            return False
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.config.llm_model,
            "is_loaded": self.llm is not None,
            "prompt_file": str(self.config.prompt_file),
            "prompt_loaded": self.prompt_template is not None
        }

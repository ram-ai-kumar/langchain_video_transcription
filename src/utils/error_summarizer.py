"""AI-based error summarizer using LangChain and Ollama."""

from pathlib import Path
from typing import Optional

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from langchain_core.runnables import RunnableSequence

from src.core.config import PipelineConfig
from src.core.exceptions import LLMProcessingError
from src.utils.error_logger import ErrorLogger


class ErrorSummarizer:
    """Summarizes errors using AI and proposes solutions."""

    def __init__(self, config: PipelineConfig, error_logger: ErrorLogger):
        """Initialize error summarizer.
        
        Args:
            config: Pipeline configuration
            error_logger: Error logger instance
        """
        self.config = config
        self.error_logger = error_logger
        self.llm = None
        self.summary_chain = None

    def _load_llm(self) -> OllamaLLM:
        """Load the LLM model if not already loaded."""
        if self.llm is None:
            try:
                self.llm = OllamaLLM(model=self.config.llm_model)
            except Exception as e:
                raise LLMProcessingError(
                    f"Failed to load LLM model '{self.config.llm_model}': {e}",
                    processor="ErrorSummarizer"
                )
        return self.llm

    def _get_summary_chain(self) -> RunnableSequence:
        """Get the error summarization chain."""
        if self.summary_chain is None:
            llm = self._load_llm()
            
            # Create prompt template for error summarization
            prompt_template = PromptTemplate.from_template(
                """You are an expert system debugger. Analyze the following errors from a video transcription pipeline and provide a concise summary with proposed solutions.

ERRORS:
{errors}

Please provide:
1. A brief summary of the error types (categorized)
2. The most common/root causes
3. Proposed solutions for each error type
4. Any configuration or setup issues that might be causing these errors

Format your response clearly with sections and bullet points. Be specific and actionable."""
            )
            
            self.summary_chain = RunnableSequence(first=prompt_template, last=llm)
        return self.summary_chain

    def summarize_errors(self) -> Optional[str]:
        """Summarize errors using AI and save to file.
        
        Returns:
            Generated summary, or None if no errors or summarization fails
        """
        # Get errors from log
        errors = self.error_logger.get_errors()
        
        if not errors or not errors.strip():
            return None
        
        try:
            # Generate summary using AI
            chain = self._get_summary_chain()
            summary = chain.invoke({"errors": errors})
            
            # Save summary to file
            self.error_logger.save_summary(summary)
            
            return summary
            
        except Exception as e:
            # If AI summarization fails, return a simple summary
            error_count = self.error_logger.get_error_count()
            simple_summary = f"Error summarization failed: {e}\n\nTotal errors logged: {error_count}\n\nDetailed errors are available at: {self.error_logger.error_log_path}"
            self.error_logger.save_summary(simple_summary)
            return simple_summary

    def get_cached_summary(self) -> Optional[str]:
        """Get the cached summary if available.
        
        Returns:
            Cached summary, or None if not available
        """
        return self.error_logger.get_summary()

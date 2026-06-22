"""Comprehensive tests for study_generator to achieve 100% coverage."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.generators.study_generator import StudyMaterialGenerator
from src.core.config import PipelineConfig
from src.core.exceptions import ProcessingError
from src.processors.base import ProcessResult


@pytest.fixture
def config(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Test prompt")
    header = tmp_path / "header.tex"
    header.write_text("Test header")
    return PipelineConfig(
        prompt_file=prompt,
        header_file=header,
        generate_pdf=False,
        target="text",
    )


@pytest.fixture
def generator(config):
    return StudyMaterialGenerator(config)


class TestInitialization:
    def test_init_with_pdf(self, tmp_path):
        prompt = tmp_path / "prompt.md"
        prompt.write_text("Test prompt")
        header = tmp_path / "header.tex"
        header.write_text("Test header")
        cfg = PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=True)
        gen = StudyMaterialGenerator(cfg)
        assert gen.pdf_generator is not None

    def test_init_without_pdf(self, generator):
        assert generator.pdf_generator is None
        assert generator._llm_processor is None


class TestGenerate:
    @patch('src.generators.study_generator.LLMProcessor')
    def test_generate_success_no_pdf(self, mock_llm_class, generator, tmp_path):
        mock_llm = Mock()
        mock_llm.process.return_value = ProcessResult(
            success=True, output_path=tmp_path / "study.md", metadata={"test": "data"}
        )
        mock_llm_class.return_value = mock_llm

        transcript = tmp_path / "transcript.txt"
        transcript.write_text("Test transcript")
        result = generator.generate(transcript)
        assert result.success is True
        assert "Successfully generated" in result.message

    @patch('src.generators.study_generator.LLMProcessor')
    def test_generate_llm_failure(self, mock_llm_class, generator, tmp_path):
        mock_llm = Mock()
        mock_llm.process.return_value = ProcessResult(
            success=False, message="LLM failed"
        )
        mock_llm_class.return_value = mock_llm

        transcript = tmp_path / "transcript.txt"
        transcript.write_text("Test transcript")
        result = generator.generate(transcript)
        assert result.success is False
        assert "Failed to generate" in result.message

    @patch('src.generators.study_generator.LLMProcessor')
    def test_generate_with_pdf_success(self, mock_llm_class, tmp_path):
        prompt = tmp_path / "prompt.md"
        prompt.write_text("Test prompt")
        header = tmp_path / "header.tex"
        header.write_text("Test header")
        cfg = PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=True, target="pdf")
        gen = StudyMaterialGenerator(cfg)

        mock_llm = Mock()
        mock_llm.process.return_value = ProcessResult(
            success=True, output_path=tmp_path / "study.md", metadata={"test": "data"}
        )
        mock_llm_class.return_value = mock_llm

        transcript = tmp_path / "transcript.txt"
        transcript.write_text("Test transcript")
        study = tmp_path / "study.md"
        study.write_text("# Study content")

        with patch.object(gen.pdf_generator, 'generate_pdf', return_value=ProcessResult(success=True, output_path=tmp_path / "study.pdf")):
            result = gen.generate(transcript)
        assert result.success is True
        assert "and PDF" in result.message

    @patch('src.generators.study_generator.LLMProcessor')
    def test_generate_with_pdf_failure(self, mock_llm_class, tmp_path):
        prompt = tmp_path / "prompt.md"
        prompt.write_text("Test prompt")
        header = tmp_path / "header.tex"
        header.write_text("Test header")
        cfg = PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=True, target="pdf")
        gen = StudyMaterialGenerator(cfg)

        mock_llm = Mock()
        mock_llm.process.return_value = ProcessResult(
            success=True, output_path=tmp_path / "study.md", metadata={"test": "data"}
        )
        mock_llm_class.return_value = mock_llm

        transcript = tmp_path / "transcript.txt"
        transcript.write_text("Test transcript")
        study = tmp_path / "study.md"
        study.write_text("# Study content")

        with patch.object(gen.pdf_generator, 'generate_pdf', return_value=ProcessResult(success=False, message="PDF failed")):
            result = gen.generate(transcript)
        assert result.success is True
        assert "PDF generation failed" in result.message

    @patch('src.generators.study_generator.LLMProcessor')
    def test_generate_with_pdf_exception(self, mock_llm_class, tmp_path):
        prompt = tmp_path / "prompt.md"
        prompt.write_text("Test prompt")
        header = tmp_path / "header.tex"
        header.write_text("Test header")
        cfg = PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=True, target="pdf")
        gen = StudyMaterialGenerator(cfg)

        mock_llm = Mock()
        mock_llm.process.return_value = ProcessResult(
            success=True, output_path=tmp_path / "study.md", metadata={"test": "data"}
        )
        mock_llm_class.return_value = mock_llm

        transcript = tmp_path / "transcript.txt"
        transcript.write_text("Test transcript")
        study = tmp_path / "study.md"
        study.write_text("# Study content")

        with patch.object(gen.pdf_generator, 'generate_pdf', side_effect=Exception("PDF crash")):
            result = gen.generate(transcript)
        assert result.success is True
        assert "PDF generation failed" in result.message

    @patch('src.generators.study_generator.LLMProcessor')
    def test_generate_exception(self, mock_llm_class, generator, tmp_path):
        mock_llm = Mock()
        mock_llm.process.side_effect = Exception("Boom")
        mock_llm_class.return_value = mock_llm

        transcript = tmp_path / "transcript.txt"
        transcript.write_text("Test transcript")
        with pytest.raises(ProcessingError):
            generator.generate(transcript)

    @patch('src.generators.study_generator.LLMProcessor')
    def test_generate_with_output_dir(self, mock_llm_class, generator, tmp_path):
        mock_llm = Mock()
        mock_llm.process.return_value = ProcessResult(
            success=True, output_path=tmp_path / "output" / "study.md", metadata={}
        )
        mock_llm_class.return_value = mock_llm

        transcript = tmp_path / "transcript.txt"
        transcript.write_text("Test transcript")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = generator.generate(transcript, output_dir=output_dir)
        assert result.success is True

    @patch('src.generators.study_generator.LLMProcessor')
    def test_generate_pdf_source_with_pdf(self, mock_llm_class, tmp_path):
        """Test generate with PDF source and PDF generation - covers line 39."""
        prompt = tmp_path / "prompt.md"
        prompt.write_text("Test prompt")
        header = tmp_path / "header.tex"
        header.write_text("Test header")
        cfg = PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=True, target="pdf")
        gen = StudyMaterialGenerator(cfg)

        mock_llm = Mock()
        mock_llm.process.return_value = ProcessResult(
            success=True, output_path=tmp_path / "study.md", metadata={}
        )
        mock_llm_class.return_value = mock_llm

        transcript = tmp_path / "transcript.txt"
        transcript.write_text('{"file_type": "pdf"}')
        study = tmp_path / "study.md"
        study.write_text("# Study content")

        with patch.object(gen, '_was_source_pdf', return_value=True), \
             patch.object(gen.pdf_generator, 'generate_pdf', return_value=ProcessResult(success=True)):
            result = gen.generate(transcript)
        assert result.success is True
        assert "and PDF" in result.message

    @patch('src.generators.study_generator.LLMProcessor')
    def test_generate_pdf_source_with_pdf_in_output_dir(self, mock_llm_class, tmp_path):
        """Test generate with PDF source and output_dir - covers line 39 with output_dir."""
        prompt = tmp_path / "prompt.md"
        prompt.write_text("Test prompt")
        header = tmp_path / "header.tex"
        header.write_text("Test header")
        cfg = PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=True, target="pdf")
        gen = StudyMaterialGenerator(cfg)

        mock_llm = Mock()
        mock_llm.process.return_value = ProcessResult(
            success=True, output_path=tmp_path / "output" / "study.md", metadata={}
        )
        mock_llm_class.return_value = mock_llm

        transcript = tmp_path / "transcript.txt"
        transcript.write_text('{"file_type": "pdf"}')
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        study = output_dir / "study.md"
        study.write_text("# Study content")

        with patch.object(gen, '_was_source_pdf', return_value=True), \
             patch.object(gen.pdf_generator, 'generate_pdf', return_value=ProcessResult(success=True)):
            result = gen.generate(transcript, output_dir=output_dir)
        assert result.success is True

    @patch('src.generators.study_generator.LLMProcessor')
    def test_generate_llm_failure_message(self, mock_llm_class, generator, tmp_path):
        """Test LLM failure message path - covers early return on line 50-55."""
        mock_llm = Mock()
        mock_llm.process.return_value = ProcessResult(
            success=False, message="LLM connection failed"
        )
        mock_llm_class.return_value = mock_llm

        transcript = tmp_path / "transcript.txt"
        transcript.write_text("Test transcript")
        result = generator.generate(transcript)
        assert result.success is False
        assert "Failed to generate study material: LLM connection failed" in result.message
        assert result.metadata == {}


class TestValidatePrerequisites:
    def test_validate_prerequisites_no_pdf(self, generator):
        validation = generator.validate_prerequisites()
        assert validation["pdf_available"] is True
        assert "overall_ready" in validation

    def test_validate_prerequisites_with_pdf(self, tmp_path):
        prompt = tmp_path / "prompt.md"
        prompt.write_text("Test prompt")
        header = tmp_path / "header.tex"
        header.write_text("Test header")
        cfg = PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=True, target="pdf")
        gen = StudyMaterialGenerator(cfg)
        with patch.object(gen.pdf_generator, 'validate_dependencies', return_value=True):
            validation = gen.validate_prerequisites()
        assert validation["pdf_available"] is True

    @patch('src.generators.study_generator.LLMProcessor')
    def test_validate_prerequisites_llm_exception(self, mock_llm_class, generator):
        mock_llm = Mock()
        mock_llm.validate_llm_connection.side_effect = Exception("LLM error")
        mock_llm_class.return_value = mock_llm
        generator.config.target = "markdown"
        validation = generator.validate_prerequisites()
        assert validation["llm_available"] is False


class TestGetGeneratorInfo:
    def test_get_generator_info_no_llm(self, generator):
        info = generator.get_generator_info()
        assert info["llm_info"] == "Not loaded (lazy)"

    @patch('src.generators.study_generator.LLMProcessor')
    def test_get_generator_info_with_llm(self, mock_llm_class, generator):
        mock_llm = Mock()
        mock_llm.get_model_info.return_value = {"model": "test"}
        mock_llm_class.return_value = mock_llm
        generator._llm_processor = mock_llm
        info = generator.get_generator_info()
        assert info["llm_info"] == {"model": "test"}

    def test_get_generator_info_with_pdf(self, tmp_path):
        prompt = tmp_path / "prompt.md"
        prompt.write_text("Test prompt")
        header = tmp_path / "header.tex"
        header.write_text("Test header")
        cfg = PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=True, target="pdf")
        gen = StudyMaterialGenerator(cfg)
        info = gen.get_generator_info()
        assert "pdf_info" in info


class TestGeneratePdfOnly:
    def test_not_requested(self, generator, tmp_path):
        result = generator.generate_pdf_only(
            tmp_path / "transcript.txt", tmp_path / "study.md", tmp_path / "study.pdf"
        )
        assert result.success is True
        assert "not requested" in result.message.lower()

    def test_missing_study_file(self, tmp_path):
        prompt = tmp_path / "prompt.md"
        prompt.write_text("Test prompt")
        header = tmp_path / "header.tex"
        header.write_text("Test header")
        cfg = PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=True, target="pdf")
        gen = StudyMaterialGenerator(cfg)
        result = gen.generate_pdf_only(
            tmp_path / "transcript.txt", tmp_path / "nonexistent.md", tmp_path / "study.pdf"
        )
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_success(self, tmp_path):
        prompt = tmp_path / "prompt.md"
        prompt.write_text("Test prompt")
        header = tmp_path / "header.tex"
        header.write_text("Test header")
        cfg = PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=True, target="pdf")
        gen = StudyMaterialGenerator(cfg)
        study = tmp_path / "study.md"
        study.write_text("# Study content")
        with patch.object(gen.pdf_generator, 'generate_pdf', return_value=ProcessResult(success=True)):
            result = gen.generate_pdf_only(tmp_path / "transcript.txt", study, tmp_path / "study.pdf")
        assert result.success is True

    def test_exception(self, tmp_path):
        prompt = tmp_path / "prompt.md"
        prompt.write_text("Test prompt")
        header = tmp_path / "header.tex"
        header.write_text("Test header")
        cfg = PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=True, target="pdf")
        gen = StudyMaterialGenerator(cfg)
        study = tmp_path / "study.md"
        study.write_text("# Study content")
        with patch.object(gen.pdf_generator, 'generate_pdf', side_effect=Exception("PDF crash")):
            result = gen.generate_pdf_only(tmp_path / "transcript.txt", study, tmp_path / "study.pdf")
        assert result.success is False
        assert "PDF generation failed" in result.message


class TestWasSourcePdf:
    def test_pdf_exists(self, generator, tmp_path):
        transcript = tmp_path / "test.txt"
        transcript.write_text("content")
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        assert generator._was_source_pdf(transcript) is True

    def test_no_pdf_no_indicators(self, generator, tmp_path):
        transcript = tmp_path / "test.txt"
        transcript.write_text("regular content")
        assert generator._was_source_pdf(transcript) is False

    def test_pdf_indicators_in_content(self, generator, tmp_path):
        transcript = tmp_path / "test.txt"
        transcript.write_text('{"file_type": "pdf", "extraction_method": "pypdf2"}')
        assert generator._was_source_pdf(transcript) is True

    def test_processed_pdf_file_indicator(self, generator, tmp_path):
        transcript = tmp_path / "test.txt"
        transcript.write_text("processed pdf file content")
        assert generator._was_source_pdf(transcript) is True

    def test_extracted_from_pdf_indicator(self, generator, tmp_path):
        transcript = tmp_path / "test.txt"
        transcript.write_text("extracted from pdf content")
        assert generator._was_source_pdf(transcript) is True

    def test_pdf_text_extraction_indicator(self, generator, tmp_path):
        transcript = tmp_path / "test.txt"
        transcript.write_text("pdf text extraction result")
        assert generator._was_source_pdf(transcript) is True

    def test_transcript_not_exists(self, generator, tmp_path):
        transcript = tmp_path / "nonexistent.txt"
        assert generator._was_source_pdf(transcript) is False

    def test_read_exception(self, generator, tmp_path):
        transcript = tmp_path / "test.txt"
        transcript.write_text("content")
        with patch('src.utils.file_utils.FileManager.safe_read_text', side_effect=Exception("Read error")):
            result = generator._was_source_pdf(transcript)
        assert result is False

# Usage (v2.0 - Object-Oriented)

[← Back to README](../README.md)

## Basic Usage

```bash
# Process with default settings
python main.py /path/to/media/folder

# Skip PDF generation
python main.py /path/to/media/folder --no-pdf

# Show detailed progress
python main.py /path/to/media/folder --verbose

# Use different models
python main.py /path/to/media/folder --whisper-model large --llm-model llama3
```

## Advanced Options

```bash
# Specify output directory
python main.py /path/to/media/folder --output-dir /output/path

# Check dependencies
python main.py /path/to/media/folder --check-deps

# Validate files without processing
python main.py /path/to/media/folder --validate-only

# Use configuration file
python main.py /path/to/media/folder --config config.json

# Disable progress spinner
python main.py /path/to/media/folder --no-spinner
```

## Configuration File Support

Create a JSON configuration file for complex setups:

```json
{
  "whisper_model": "large",
  "llm_model": "gemma3",
  "generate_pdf": true,
  "verbose": true,
  "show_spinner": true,
  "output_dir": "/custom/output"
}
```

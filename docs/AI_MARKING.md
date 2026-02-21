# AI Content Marking

This document describes the AI content marking functionality that automatically adds watermarks, attribution, and acknowledgment pages to all AI-generated PDFs.

## Overview

The AI content marking system ensures transparency and proper attribution for all AI-generated study materials. When enabled, it automatically adds:

1. **Watermark**: "AI Generated Content" watermark on all pages
2. **Footer**: Author attribution in the footer of each page
3. **Acknowledgment Page**: Dedicated page with full attribution and utility information

## Features

### Watermarking

- **Text**: "AI Generated Content"
- **Position**: Center of each page
- **Rotation**: 45 degrees (diagonal)
- **Opacity**: 30% (light gray, non-intrusive)
- **Font Size**: 48pt (large but transparent)

### Attribution Footer

- **Content**: "Ram Kumar, saas.expert.ram@gmail.com"
- **Position**: Bottom center of each page
- **Style**: Italic, small font, dark gray
- **Replaces**: Default "Generated Study Material" footer

### Acknowledgment Page

Added as the last page of every AI-generated PDF with:

- **Author Information**: Name and email
- **Utility Description**: Overview of the automated system
- **Technical Features**: List of key capabilities
- **Architecture Highlights**: Design principles and patterns
- **Generation Timestamp**: When the PDF was created

## Usage

### Command Line Options

```bash
# Enable AI marking (default)
python main.py ./data

# Disable AI marking
python main.py ./data --no-ai-marking

# Disable PDF generation entirely
python main.py ./data --no-pdf
```

### Configuration

AI marking can be configured through the `PipelineConfig`:

```python
from src.domain.ai_marking import AIMarkingConfig, AuthorInfo, WatermarkConfig

# Custom configuration
custom_config = AIMarkingConfig(
    author_info=AuthorInfo(
        name="Custom Author",
        email="custom@example.com"
    ),
    watermark_config=WatermarkConfig(
        text="Custom AI Content",
        opacity=0.2,
        rotation=30
    ),
    enable_watermark=True,
    enable_attribution=True,
    enable_acknowledgment=True
)

config = PipelineConfig(
    enable_ai_marking=True,
    ai_marking_config=custom_config
)
```

## Technical Implementation

### Architecture

The AI marking system follows Domain-Driven Design principles:

- **Value Objects**: `AuthorInfo`, `WatermarkConfig`, `AIMarkingConfig`
- **Enhanced Generator**: `EnhancedPDFGenerator` extends base `PDFGenerator`
- **LaTeX Integration**: Uses `draftwatermark` package for watermarking
- **Fallback Support**: Graceful degradation when LaTeX packages unavailable

### File Structure

```
src/
├── domain/
│   └── ai_marking.py          # Domain value objects
├── generators/
│   ├── pdf_generator.py        # Base PDF generator
│   └── enhanced_pdf_generator.py  # Enhanced with AI marking
└── core/
    └── config.py              # Updated with AI marking config
```

### Dependencies

- **LaTeX**: `draftwatermark` package for watermarking
- **Pandoc**: PDF generation with custom headers
- **Python**: Standard library + existing dependencies

## Examples

### Before AI Marking

```
Generated Study Material
```

### After AI Marking

```
Ram Kumar, saas.expert.ram@gmail.com
```

### Watermark Example

```
[Diagonal "AI Generated Content" watermark across page]
```

### Acknowledgment Page Example

```markdown
# Acknowledgment

This study material was generated using an automated utility script created by:

**Ram Kumar**  
saas.expert.ram@gmail.com

## About This Utility

This Python-based system demonstrates advanced software engineering principles...
```

## Testing

### Unit Tests

```bash
# Run AI marking tests
python -m pytest tests/test_ai_marking.py -v
```

### Integration Test

```bash
# Run integration demo
python test_ai_marking_integration.py
```

### Demo

```bash
# Run full demo
python demo_ai_marking.py
```

## Benefits

1. **Transparency**: Clear identification of AI-generated content
2. **Attribution**: Proper credit to the author/utility creator
3. **Professionalism**: Consistent branding and acknowledgment
4. **Traceability**: Easy identification of generated materials
5. **Configurability**: Customizable watermarks and attribution
6. **Graceful Degradation**: Works even when some features fail

## Configuration Options

### WatermarkConfig

| Parameter | Default | Description |
|-----------|----------|-------------|
| `text` | "AI Generated Content" | Watermark text |
| `opacity` | 0.3 | Transparency (0.0-1.0) |
| `rotation` | 45 | Angle in degrees |
| `font_size` | 48 | Font size in points |
| `color` | "#CCCCCC" | Hex color code |

### AuthorInfo

| Parameter | Default | Description |
|-----------|----------|-------------|
| `name` | "Ram Kumar" | Author name |
| `email` | "saas.expert.ram@gmail.com" | Author email |

### AIMarkingConfig

| Parameter | Default | Description |
|-----------|----------|-------------|
| `enable_watermark` | True | Enable watermarking |
| `enable_attribution` | True | Enable footer attribution |
| `enable_acknowledgment` | True | Enable acknowledgment page |

## Troubleshooting

### Watermark Not Visible

- Check that `draftwatermark` LaTeX package is installed
- Verify Pandoc is using XeLaTeX or LuaLaTeX
- Ensure opacity is not too low (try 0.5+)

### Attribution Not Showing

- Verify `fancyhdr` package is available
- Check that AI marking is enabled in configuration
- Ensure header file is properly formatted

### Acknowledgment Page Missing

- Check that `enable_acknowledgment` is True
- Verify markdown processing is working
- Check for LaTeX compilation errors

## Future Enhancements

Planned improvements to AI marking:

1. **Custom Watermark Images**: Support for image watermarks
2. **Multiple Languages**: Localized acknowledgment pages
3. **QR Codes**: Links to original source/utility
4. **Digital Signatures**: Cryptographic verification
5. **Template System**: Customizable acknowledgment templates

## Security Considerations

- Watermarks are non-intrusive but visible
- Attribution cannot be easily removed
- Acknowledgment pages are embedded in PDF
- No sensitive information is exposed

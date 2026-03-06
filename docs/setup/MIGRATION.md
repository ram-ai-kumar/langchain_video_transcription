# Migration from v1.0 (Script) to v2.0 (OO)

[← Back to README](../README.md)

## What Changed

1. **Entry Point**: `python video_transcribe.py` → `python main.py`
2. **Configuration**: Command-line arguments now use modern CLI patterns
3. **Architecture**: Modular object-oriented design replaces monolithic script
4. **Error Handling**: Structured exception hierarchy with detailed error messages
5. **Testing**: Each component can be tested independently

## Migration Steps

1. **Update your workflow**:

   ```bash
   # Old
   python video_transcribe.py /path/to/media --no-pdf

   # New
   python main.py /path/to/media --no-pdf
   ```

2. **Configuration files**: Move any custom `study_prompt.txt` to `config/` directory

3. **Custom processors**: Extend `BaseProcessor` class instead of adding functions

## Backward Compatibility

The Object Oriented implementation maintains full backward compatibility:

- Same input/output file formats
- Same processing logic and quality
- Same configuration options (with improved CLI)
- Same generated study material structure

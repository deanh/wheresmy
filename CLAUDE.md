# Wheresmy - Image Metadata Extractor Project

## Commands
- **Run metadata extractor**: `python image-metadata-extractor.py -f <file>` or `python image-metadata-extractor.py -d <directory>`
- **Sample files**: `python sample-files.py <source> <destination> <count>`
- **Run notebooks**: `jupyter lab`
- **Install dependencies**: `pip install -r requirements.txt`
- **Format code**: `black .`
- **Lint code**: `flake8 .`

## Code Style Guidelines
- **Imports**: Group standard library, third-party, and local imports with a blank line between groups
- **Type hints**: Use Python type hints for function parameters and return values
- **Docstrings**: Include docstrings for all functions, classes, and modules using triple quotes
- **Function length**: Keep functions focused and under 50 lines when possible
- **Error handling**: Use try/except blocks with specific exception types
- **Naming**: Use snake_case for variables/functions, PascalCase for classes
- **Constants**: Define constants at module level using UPPER_CASE
- **Comments**: Add comments for complex logic, not obvious code
- **Indentation**: 4 spaces (no tabs)
- **Line length**: Maximum 100 characters per line

## Tool Information
This project extracts and processes image metadata from various formats including JPEG, PNG, HEIC, etc.
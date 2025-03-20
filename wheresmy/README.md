# Wheresmy Package Structure

This package contains the modular components of the Wheresmy image search system:

## Directory Structure

- **core/**: Core functionality modules
  - `database.py`: Database access and management
  - `metadata_extractor.py`: Image metadata extraction
  - `vlm_describers.py`: Vision-language model image description

- **utils/**: Utility modules
  - `apple_makernote.py`: Apple makernote EXIF data decoder

- **search/**: Search-related modules
  - `search.py`: Image search functionality
  - `stats.py`: Database statistics

- **cli/**: Command-line interface modules
  - `search_cli.py`: CLI for searching images
  - `import_metadata.py`: CLI for importing metadata
  - `run_web.py`: CLI for running the web server

- **tests/**: Test modules
  - `test_integration.py`: End-to-end integration tests
  - `test_content_search.py`: Content-based search tests
  - `test_search.py`: Basic search tests
  - `test_metadata_extractor.py`: Metadata extraction tests
  - `test_vlm_describers.py`: VLM describer tests

- **web_app.py**: Flask web application
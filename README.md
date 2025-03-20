# Where's My Photo

A local image search application that uses extracted metadata and AI-generated descriptions to help you find photos in your personal collection.

## Features

- **Metadata Extraction**: Extracts comprehensive metadata from various image formats (JPEG, PNG, HEIC, etc.)
- **AI-Powered Descriptions**: Uses Vision-Language Models to generate searchable descriptions of photos
- **Full-Text Search**: Find images by searching their content, not just filenames
- **Database Storage**: Efficiently organizes and retrieves photo metadata
- **Responsive Web Interface**: Easy-to-use search interface with filters and previews
- **Low Resource Usage**: Designed to run on machines with 4-8GB of RAM

## System Components

The project is organized as a Python package with modular components:

### 1. Core Components (`wheresmy/core/`)
- **Database** (`database.py`): SQLite database with full-text search
- **Metadata Extractor** (`metadata_extractor.py`): Extracts EXIF data, camera info, GPS
- **VLM Integration** (`vlm_describers.py`): Generates image descriptions with SmolVLM

### 2. Search Tools (`wheresmy/search/`)
- **Search Utilities** (`search.py`): Functions for searching images
- **Statistics Utilities** (`stats.py`): Functions for database statistics

### 3. User Interfaces
- **Web Interface** (`wheresmy/web_app.py`): Flask-based responsive UI
- **CLI Tools** (`wheresmy/cli/`): Command-line interfaces

### 4. Utilities (`wheresmy/utils/`)
- **Apple MakerNote Decoder** (`apple_makernote.py`): iOS metadata decoder

## Quick Start

```bash
# 1. Install the package (optional)
# pip install -e .  # Install in development mode

# 2. Extract metadata from images
python wheresmy/core/metadata_extractor.py -d sample_directory -o metadata.json

# 3. Import metadata to the database
./wheresmy_import metadata.json --db photos.db

# 4. Search images from the command line
./wheresmy_search --db photos.db search --query "beach sunset"

# 5. Start the web application
./wheresmy_web --db photos.db

# 6. Open in browser: http://localhost:5000
```

See [USAGE.md](USAGE.md) for detailed instructions and command options.

## Prerequisites

- Python 3.8+
- 4-8GB RAM
- Local photo collection

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/wheresmy.git
   cd wheresmy
   ```

2. Install the package and dependencies:
   ```bash
   # Option 1: Install dependencies only
   pip install -r requirements.txt
   
   # Option 2: Install the package in development mode (recommended)
   pip install -e .
   ```

3. Make the launcher scripts executable:
   ```bash
   chmod +x wheresmy_*
   ```

## Features in Detail

### Metadata Extraction

The application extracts rich metadata from images, including:
- Basic image properties (format, dimensions, color mode)
- EXIF data (camera, date/time, exposure settings)
- GPS coordinates and location information
- Apple MakerNote data for iOS devices
- AI-generated image descriptions using Vision-Language Models

### Smart Search

The search functionality allows you to:
- Search by text content from VLM-generated descriptions
- Filter by camera make and model
- Filter by date ranges
- View image details including EXIF data
- Browse images with a responsive grid interface

## License

MIT License

## Acknowledgments

- Uses Hugging Face Transformers for VLM models
- Built with Flask and SQLite FTS5
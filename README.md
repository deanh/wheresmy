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

### 1. Metadata Extractor (`image_metadata_extractor.py`)
- Extracts EXIF data, camera information, GPS coordinates
- Decodes Apple MakerNote data from iOS devices
- Supports common image formats (JPEG, PNG, HEIC, etc.)

### 2. VLM Integration (`vlm_describers.py`)
- Uses SmolVLM to describe image content
- Provides semantic descriptions searchable by natural language
- Enables content-based searching

### 3. Database Storage (`image_database.py`)
- SQLite database with full-text search capabilities
- Efficient storage of metadata with indexing for fast queries
- Supports filtering by date, camera, dimensions, etc.

### 4. Web Interface (`web_app.py`)
- Simple, responsive UI for searching and viewing photos
- Filter by text, camera, date, etc.
- Image preview with detailed metadata display

## Quick Start

```bash
# 1. Extract metadata from images
python image_metadata_extractor.py -d sample_directory -o metadata.json

# 2. Import metadata to the database
python import_metadata.py metadata.json --db photos.db

# 3. Start the web application
python run_web.py --db photos.db

# 4. Open in browser: http://localhost:5000
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

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
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
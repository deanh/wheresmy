# Where's My Photo - Usage Guide

This document provides a guide on how to use the Where's My Photo application.

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

## Step 1: Extract Metadata from Images

First, you need to extract metadata from your images:

```bash
# Process a single image
python image_metadata_extractor.py -f /path/to/your/image.jpg -o metadata.json

# Process a directory of images
python image_metadata_extractor.py -d /path/to/your/photos -o metadata.json

# Process recursively with AI-generated descriptions
python image_metadata_extractor.py -d /path/to/your/photos -r --vlm smolvlm -o metadata.json
```

## Step 2: Import Metadata to the Search Database

Next, import the metadata into the search database:

```bash
# Import the metadata
python import_metadata.py metadata.json --db photo_search.db
```

## Step 3: Start the Web Application

Finally, start the web application to search your photos:

```bash
# Start the web app
python run_web.py --db photo_search.db
```

Open your browser and navigate to: http://localhost:5000

## Example Workflow

Here's a complete example workflow using sample images:

```bash
# Extract metadata from the sample directory
python image_metadata_extractor.py -d sample_directory -o photos.json

# Import the metadata into the search database
python import_metadata.py photos.json --db photos.db

# Start the web app
python run_web.py --db photos.db
```

## Command Line Options

### Metadata Extraction

```
-f, --file FILE         Path to the image file
-d, --directory DIR     Path to directory containing images
-o, --output FILE       Output JSON file (optional)
-r, --recursive         Process directories recursively
--vlm {none,smolvlm}    Use VLM to generate image descriptions
--vlm-prompt TEXT       Custom prompt for VLM description generation
--cache-dir DIR         Directory to cache VLM models
```

### Database Import

```
--db FILE               Path to the database file (default: image_metadata.db)
```

### Web Application

```
--host HOST             Host to bind to (default: 0.0.0.0)
--port PORT             Port to listen on (default: 5000)
--db FILE               Path to the database file (default: image_metadata.db)
--debug                 Run in debug mode
```

## Best Practices

1. **Processing Large Collections**: Break large collections into smaller batches
2. **Using VLM Descriptions**: VLM processing takes time but improves search results
3. **Database Management**: Use separate database files for different collections
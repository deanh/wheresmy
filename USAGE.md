# Where's My Photo - Usage Guide

This document provides a guide on how to use the Where's My Photo application.

## Quick Start

```bash
# 1. Extract metadata from images
python -m wheresmy.core.metadata_extractor -d sample_directory -o metadata.json

# 2. Import metadata to the database
./wheresmy_import metadata.json --db photos.db

# 3. Start the web application
./wheresmy_web --db photos.db

# 4. Open in browser: http://localhost:5000
```

## Step 1: Extract Metadata from Images

First, you need to extract metadata from your images:

```bash
# Process a single image
python -m wheresmy.core.metadata_extractor -f /path/to/your/image.jpg -o metadata.json

# Process a directory of images
python -m wheresmy.core.metadata_extractor -d /path/to/your/photos -o metadata.json

# Process recursively with AI-generated descriptions
python -m wheresmy.core.metadata_extractor -d /path/to/your/photos -r --vlm smolvlm -o metadata.json
```

## Step 2: Import Metadata to the Search Database

Next, import the metadata into the search database:

```bash
# Import the metadata
./wheresmy_import metadata.json --db photo_search.db
```

## Step 3: Search from Command Line (Optional)

You can search your photos from the command line:

```bash
# Basic search
./wheresmy_search --db photo_search.db search --query "beach sunset"

# Get database statistics
./wheresmy_search --db photo_search.db stats
```

## Step 4: Start the Web Application

Finally, start the web application to search your photos:

```bash
# Start the web app
./wheresmy_web --db photo_search.db
```

Open your browser and navigate to: http://localhost:5000

## Example Workflow

Here's a complete example workflow using sample images:

```bash
# Extract metadata from the sample directory
python -m wheresmy.core.metadata_extractor -d sample_directory -o photos.json

# Import the metadata into the search database
./wheresmy_import photos.json --db photos.db

# Search for photos
./wheresmy_search --db photos.db search --query "nature"

# Start the web app
./wheresmy_web --db photos.db
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

### Database Import (wheresmy_import)

```
--db FILE               Path to the database file (default: image_metadata.db)
```

### Search Tool (wheresmy_search)

```
# Global options
--db FILE               Path to the database file (default: image_metadata.db)

# Search subcommand options
search --query TEXT     Search query string
search --limit NUM      Maximum number of results to return
search --camera TEXT    Filter by camera make/model

# Stats subcommand
stats                   Show database statistics
```

### Web Application (wheresmy_web)

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
4. **Python Module Path**: When calling directly, use module notation (python -m wheresmy.core.metadata_extractor)
5. **Development**: Install the package in development mode (pip install -e .) for easier testing
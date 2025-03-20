#!/bin/bash
# Clean and load script for wheresmy
# Cleans up temporary files and loads sample data

set -e  # Exit on error

echo "=== Cleaning up temporary files ==="
rm -f *.db sample_*.json
rm -rf wheresmy/static/images/thumbnails/*

echo "=== Creating directories ==="
mkdir -p wheresmy/static/images/thumbnails

echo "=== Extracting metadata from sample images ==="
python -m wheresmy.core.metadata_extractor -d sample_directory -o sample_metadata.json

echo "=== Importing metadata and generating thumbnails ==="
./wheresmy_import sample_metadata.json --db sample_photos.db

echo "=== Database stats ==="
sqlite3 sample_photos.db "SELECT COUNT(*) AS 'Total images' FROM images;"
sqlite3 sample_photos.db "SELECT camera_make, camera_model, COUNT(*) FROM images GROUP BY camera_make, camera_model;"

echo ""
echo "=== All done! ==="
echo "To start the web application, run:"
echo "./wheresmy_web --db sample_photos.db"
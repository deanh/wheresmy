#!/usr/bin/env python3
"""
Simple script to import JSON metadata into the database.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

from wheresmy.core.database import ImageDatabase
from wheresmy.utils.thumbnail import create_thumbnail

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
THUMBNAIL_DIR = os.path.join('wheresmy', 'static', 'images', 'thumbnails')

def import_metadata(json_path, db_path):
    """Import metadata from a JSON file into the database."""
    # Check if the file exists
    if not os.path.exists(json_path):
        logger.error(f"JSON file not found: {json_path}")
        return False
    
    # Initialize database
    logger.info(f"Initializing database at {db_path}")
    db = ImageDatabase(db_path)
    
    # Load JSON metadata
    logger.info(f"Loading metadata from {json_path}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        return False
    
    # Make sure thumbnail directory exists
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    thumbnail_path = os.path.join(project_root, THUMBNAIL_DIR)
    os.makedirs(thumbnail_path, exist_ok=True)
    
    # Check if it's a single image or a directory
    if isinstance(metadata, dict) and "filename" in metadata:
        # Single image
        logger.info(f"Importing metadata for a single image: {metadata['filename']}")
        
        # Add file_path if not present (using the filename)
        if "file_path" not in metadata:
            # Use the JSON filename as a base, remove .json and add the image extension
            file_path = os.path.splitext(json_path)[0]
            if "format" in metadata:
                ext = metadata["format"].lower()
                file_path = file_path + "." + ext
            metadata["file_path"] = file_path
        
        # Create thumbnail if file_path exists
        if "file_path" in metadata and metadata["file_path"]:
            logger.info(f"Creating thumbnail for {metadata['filename']}")
            thumbnail = create_thumbnail(metadata["file_path"], thumbnail_path)
            if thumbnail:
                # Add thumbnail path to metadata
                metadata["thumbnail"] = os.path.join("static", "images", "thumbnails", thumbnail)
        
        # Add to database
        db.add_image(metadata)
        count = 1
    elif isinstance(metadata, dict):
        # Directory of images
        logger.info(f"Importing metadata for multiple images")
        
        # Count valid entries
        count = 0
        for path, img_metadata in metadata.items():
            # Add file_path if not present
            if "file_path" not in img_metadata:
                img_metadata["file_path"] = path
            
            # Create thumbnail if file_path exists
            if "file_path" in img_metadata and img_metadata["file_path"]:
                filename = os.path.basename(img_metadata["file_path"])
                logger.info(f"Creating thumbnail for {filename}")
                thumbnail = create_thumbnail(img_metadata["file_path"], thumbnail_path)
                if thumbnail:
                    # Add thumbnail path to metadata
                    img_metadata["thumbnail"] = os.path.join("static", "images", "thumbnails", thumbnail)
            
            # Add to database
            db.add_image(img_metadata)
            count += 1
            
            # Log progress
            if count % 10 == 0:
                logger.info(f"Imported {count} images so far")
    else:
        logger.error("Unsupported metadata format")
        return False
    
    # Get stats
    stats = db.get_stats()
    logger.info(f"Successfully imported {count} images")
    logger.info(f"Database now contains {stats['total_images']} images")
    
    return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Import metadata into the database")
    parser.add_argument("json_path", help="Path to the JSON metadata file")
    parser.add_argument("--db", default="image_metadata.db", help="Path to the database file")
    
    args = parser.parse_args()
    
    success = import_metadata(args.json_path, args.db)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
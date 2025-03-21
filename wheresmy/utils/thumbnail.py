#!/usr/bin/env python3
"""
Thumbnail Generation Utility

This module provides functions for generating image thumbnails.
"""

import os
import logging
from pathlib import Path
from PIL import Image, UnidentifiedImageError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_thumbnail(image_path, output_dir, size=(300, 300), format="JPEG"):
    """
    Create a thumbnail for an image.

    Args:
        image_path: Path to the original image
        output_dir: Directory to save the thumbnail
        size: Thumbnail dimensions as (width, height) tuple
        format: Output format (default: JPEG)

    Returns:
        Path to the thumbnail or None if creation failed
    """
    # Ensure the filename is safe for storage
    filename = os.path.basename(image_path)
    # Replace spaces with underscores for cleaner URLs
    safe_filename = filename.replace(" ", "_")
    thumbnail_path = os.path.join(output_dir, f"thumb_{safe_filename}")

    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Check if thumbnail already exists
    if os.path.exists(thumbnail_path):
        return thumbnail_path

    # Convert relative path to absolute if needed
    if not os.path.isabs(image_path):
        # Go up one level from utils to the package root
        package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Go up one more level to the project root
        project_root = os.path.dirname(package_root)
        abs_image_path = os.path.join(project_root, image_path)
    else:
        abs_image_path = image_path

    try:
        # Open and create thumbnail
        img = Image.open(abs_image_path)
        img.thumbnail(size)

        # Convert RGBA to RGB if saving as JPEG
        if format.upper() == "JPEG" and img.mode == "RGBA":
            # Create a white background image
            background = Image.new("RGB", img.size, (255, 255, 255))
            # Composite the image with the background
            background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
            img = background

        # Save thumbnail
        img.save(thumbnail_path, format)
        logger.info(f"Created thumbnail: {thumbnail_path}")

        # Return relative path from output_dir
        return os.path.basename(thumbnail_path)
    except (IOError, UnidentifiedImageError) as e:
        logger.error(f"Error creating thumbnail for {image_path}: {str(e)}")
        return None

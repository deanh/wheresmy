#!/usr/bin/env python3
"""
Image Search Web Application

This module provides a Flask-based web interface for searching
the image metadata database. It allows users to search for images
using text queries, date ranges, and other filters.
"""

import os

# import json
# import base64
import logging

# from datetime import datetime
# from typing import Dict, List, Optional, Any
from pathlib import Path

from flask import (
    Flask,
    request,
    jsonify,
    send_file,
    render_template,
    abort,
)  # , Response
from flask_cors import CORS

from wheresmy.core.database import ImageDatabase
from wheresmy.search import search as search_utils
from wheresmy.search import stats as stats_utils

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)  # Enable CORS for all routes

# Initialize database
db = ImageDatabase()

# Constants
THUMBNAIL_SIZE = (300, 300)
# We no longer need this, as thumbnails are generated during import
# THUMBNAIL_CACHE_DIR = ".image_cache/thumbnails"


def ensure_dir_exists(directory: str) -> None:
    """Ensure a directory exists, creating it if necessary."""
    Path(directory).mkdir(parents=True, exist_ok=True)


# Routes
@app.route("/")
def home():
    """Render the home page."""
    return render_template("index.html")


@app.route("/api/search")
def search():
    """
    Search for images.

    Query parameters:
    - q: Text query
    - camera_make: Camera manufacturer
    - camera_model: Camera model
    - date_start: Start date (ISO format)
    - date_end: End date (ISO format)
    - min_width: Minimum image width
    - min_height: Minimum image height
    - limit: Maximum number of results (default: 100)
    - offset: Number of results to skip (default: 0)
    """
    # Parse query parameters
    query = request.args.get("q", "")
    camera_make = request.args.get("camera_make")
    camera_model = request.args.get("camera_model")
    date_start = request.args.get("date_start")
    date_end = request.args.get("date_end")
    min_width = request.args.get("min_width")
    min_height = request.args.get("min_height")

    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    # Convert numeric parameters
    if min_width:
        min_width = int(min_width)
    if min_height:
        min_height = int(min_height)

    # Perform search using the utility module
    results = search_utils.search_images(
        db,
        text_query=query,
        camera_make=camera_make,
        camera_model=camera_model,
        date_start=date_start,
        date_end=date_end,
        min_width=min_width,
        min_height=min_height,
        limit=limit,
        offset=offset,
    )

    # Process results
    processed_results = []
    for result in results:
        # The thumbnail should be pre-generated during import
        # If it exists in the metadata, use it directly

        # Add thumbnail URL to result
        processed_result = {
            "id": result["id"],
            "filename": result["filename"],
            "file_path": result["file_path"],
            # If thumbnail exists in the result, use it, otherwise use a placeholder
            "thumbnail": result.get("thumbnail", "/static/placeholder.jpg"),
            "width": result["width"],
            "height": result["height"],
            "format": result["format"],
            "capture_date": result["capture_date"],
            "camera_make": result["camera_make"],
            "camera_model": result["camera_model"],
            "description": result["description"],
            "gps_lat": result["gps_lat"],
            "gps_lon": result["gps_lon"],
        }

        processed_results.append(processed_result)

    return jsonify(
        {
            "results": processed_results,
            "total": len(processed_results),
            "offset": offset,
            "limit": limit,
        }
    )


@app.route("/api/stats")
def get_stats():
    """Get database statistics."""
    date_interval = request.args.get("date_interval", "month")

    # Get all statistics using the utility module
    statistics = stats_utils.get_all_statistics(db, date_interval=date_interval)

    return jsonify(statistics)


# We no longer need this route as thumbnails are served from static
# @app.route('/thumbnails/<filename>')
# def serve_thumbnail(filename):
#     """Serve a thumbnail file."""
#     abort(404)


@app.route("/api/image/<int:image_id>")
def get_image(image_id):
    """Get detailed information about an image."""
    # Use the utility module to get the image by ID
    image_data = search_utils.get_image_by_id(db, image_id)

    if not image_data:
        abort(404)

    # Return all available metadata
    return jsonify(image_data)


@app.route("/image/<int:image_id>")
def serve_image(image_id):
    """Serve an image file."""
    # Get image data using the utility module
    image_data = search_utils.get_image_by_id(db, image_id)

    if not image_data:
        abort(404)

    image_path = image_data.get("file_path")

    if not image_path or not os.path.exists(image_path):
        abort(404)

    return send_file(image_path)


def create_placeholder_image():
    """Create a placeholder image for missing thumbnails."""
    from PIL import Image, ImageDraw

    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    placeholder_path = os.path.join(static_dir, "placeholder.jpg")

    if os.path.exists(placeholder_path):
        return

    # Create directory if it doesn't exist
    os.makedirs(static_dir, exist_ok=True)

    # Create placeholder image
    img = Image.new("RGB", (300, 300), color="#e0e0e0")
    d = ImageDraw.Draw(img)

    # Draw text
    d.text((150, 150), "No Image", fill=(100, 100, 100), anchor="mm")

    # Save image
    img.save(placeholder_path)
    logger.info(f"Created placeholder image: {placeholder_path}")


def main():
    """Main function to start the web application."""
    parser = argparse.ArgumentParser(
        description="Start the image search web application"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to run the server on"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument(
        "--db", default="image_metadata.db", help="Path to database file"
    )
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")

    args = parser.parse_args()

    # Set database path
    global db
    db = ImageDatabase(args.db)

    # Ensure static and templates directories
    # Now these directories are relative to the package
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    templates_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "templates"
    )

    ensure_dir_exists(static_dir)
    ensure_dir_exists(templates_dir)
    ensure_dir_exists(os.path.join(static_dir, "js"))
    ensure_dir_exists(os.path.join(static_dir, "css"))
    ensure_dir_exists(os.path.join(static_dir, "images", "thumbnails"))

    # Create placeholder image
    create_placeholder_image()

    # Log database stats
    stats = db.get_stats()
    logger.info(f"Starting web app with {stats['total_images']} images in database")

    # Run the application
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    import argparse

    main()

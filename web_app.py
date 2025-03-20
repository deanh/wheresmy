#!/usr/bin/env python3
"""
Image Search Web Application

This module provides a Flask-based web interface for searching
the image metadata database. It allows users to search for images
using text queries, date ranges, and other filters.
"""

import os
import json
import base64
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from flask import Flask, request, jsonify, send_file, render_template, abort, Response
from flask_cors import CORS

from image_database import ImageDatabase

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Enable CORS for all routes

# Initialize database
db = ImageDatabase()

# Constants
THUMBNAIL_SIZE = (300, 300)
THUMBNAIL_CACHE_DIR = ".image_cache/thumbnails"

def ensure_dir_exists(directory: str) -> None:
    """Ensure a directory exists, creating it if necessary."""
    Path(directory).mkdir(parents=True, exist_ok=True)

ensure_dir_exists(THUMBNAIL_CACHE_DIR)

# Helpers
def get_thumbnail_path(image_path: str) -> str:
    """Get the path to the thumbnail for an image."""
    # Use base64-encoded path as the thumbnail filename to avoid special characters
    encoded_path = base64.b64encode(image_path.encode()).decode()
    return os.path.join(THUMBNAIL_CACHE_DIR, f"{encoded_path}.jpg")

def create_thumbnail(image_path: str, size=THUMBNAIL_SIZE) -> str:
    """Create a thumbnail for an image if it doesn't exist."""
    from PIL import Image, UnidentifiedImageError
    
    thumbnail_path = get_thumbnail_path(image_path)
    
    # Check if thumbnail already exists
    if os.path.exists(thumbnail_path):
        return thumbnail_path
        
    try:
        # Create thumbnail directory if it doesn't exist
        os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
        
        # Open the image
        img = Image.open(image_path)
        
        # Create thumbnail
        img.thumbnail(size)
        
        # Save thumbnail
        img.save(thumbnail_path, "JPEG")
        
        return thumbnail_path
    except (IOError, UnidentifiedImageError) as e:
        logger.error(f"Error creating thumbnail for {image_path}: {str(e)}")
        return ""

# Routes
@app.route('/')
def home():
    """Render the home page."""
    return render_template('index.html')

@app.route('/api/search')
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
    query = request.args.get('q', '')
    camera_make = request.args.get('camera_make')
    camera_model = request.args.get('camera_model')
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')
    min_width = request.args.get('min_width')
    min_height = request.args.get('min_height')
    
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    # Convert numeric parameters
    if min_width:
        min_width = int(min_width)
    if min_height:
        min_height = int(min_height)
    
    # Perform search
    results = db.filter_search(
        text_query=query,
        camera_make=camera_make,
        camera_model=camera_model,
        date_start=date_start,
        date_end=date_end,
        min_width=min_width,
        min_height=min_height,
        limit=limit,
        offset=offset
    )
    
    # Process results
    processed_results = []
    for result in results:
        # Create thumbnail if it doesn't exist
        file_path = result.get('file_path')
        
        if file_path and os.path.exists(file_path):
            # Try to create thumbnail
            try:
                thumbnail_path = create_thumbnail(file_path)
                relative_thumb = os.path.relpath(thumbnail_path, app.static_folder) if thumbnail_path else None
            except Exception as e:
                logger.error(f"Error creating thumbnail: {str(e)}")
                relative_thumb = None
        else:
            relative_thumb = None
            
        # Add thumbnail URL to result
        processed_result = {
            'id': result['id'],
            'filename': result['filename'],
            'file_path': result['file_path'],
            'thumbnail': f"/thumbnails/{os.path.basename(thumbnail_path)}" if relative_thumb else None,
            'width': result['width'],
            'height': result['height'],
            'format': result['format'],
            'capture_date': result['capture_date'],
            'camera_make': result['camera_make'],
            'camera_model': result['camera_model'],
            'description': result['description'],
            'gps_lat': result['gps_lat'],
            'gps_lon': result['gps_lon']
        }
        
        processed_results.append(processed_result)
    
    return jsonify({
        'results': processed_results,
        'total': len(processed_results),
        'offset': offset,
        'limit': limit
    })

@app.route('/api/stats')
def get_stats():
    """Get database statistics."""
    stats = db.get_stats()
    
    # Get camera stats
    camera_stats = db.get_camera_stats()
    
    # Get date stats
    date_interval = request.args.get('date_interval', 'month')
    date_stats = db.get_date_stats(by=date_interval)
    
    return jsonify({
        'stats': stats,
        'cameras': camera_stats,
        'dates': date_stats
    })

@app.route('/thumbnails/<filename>')
def serve_thumbnail(filename):
    """Serve a thumbnail file."""
    # Find the thumbnail in the cache directory
    for root, _, files in os.walk(THUMBNAIL_CACHE_DIR):
        if filename in files:
            return send_file(os.path.join(root, filename))
    
    abort(404)

@app.route('/api/image/<int:image_id>')
def get_image(image_id):
    """Get detailed information about an image."""
    # Use the database's search function to get the image by ID
    results = db.filter_search(f"id:{image_id}", limit=1)
    
    if not results:
        abort(404)
        
    image_data = results[0]
    
    # Return all available metadata
    return jsonify(image_data)

@app.route('/image/<int:image_id>')
def serve_image(image_id):
    """Serve an image file."""
    # Get image data from database
    results = db.filter_search(f"id:{image_id}", limit=1)
    
    if not results:
        abort(404)
        
    image_path = results[0].get('file_path')
    
    if not image_path or not os.path.exists(image_path):
        abort(404)
        
    return send_file(image_path)

def create_placeholder_image():
    """Create a placeholder image for missing thumbnails."""
    from PIL import Image, ImageDraw
    
    static_dir = 'static'
    placeholder_path = os.path.join(static_dir, 'placeholder.jpg')
    
    if os.path.exists(placeholder_path):
        return
        
    # Create directory if it doesn't exist
    os.makedirs(static_dir, exist_ok=True)
    
    # Create placeholder image
    img = Image.new('RGB', (300, 300), color='#e0e0e0')
    d = ImageDraw.Draw(img)
    
    # Draw text
    d.text((150, 150), "No Image", fill=(100, 100, 100), anchor="mm")
    
    # Save image
    img.save(placeholder_path)
    print(f"Created placeholder image: {placeholder_path}")

def main():
    """Main function to start the web application."""
    parser = argparse.ArgumentParser(description="Start the image search web application")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--db", default="image_metadata.db", help="Path to database file")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    # Set database path
    global db
    db = ImageDatabase(args.db)
    
    # Ensure static and templates directories
    ensure_dir_exists('static')
    ensure_dir_exists('templates')
    ensure_dir_exists('static/js')
    ensure_dir_exists('static/css')
    
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
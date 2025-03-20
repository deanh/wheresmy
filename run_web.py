#!/usr/bin/env python3
"""
Simple script to run the web application.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

from web_app import app
from image_database import ImageDatabase

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to start the web server."""
    parser = argparse.ArgumentParser(description="Start the web application")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--db", default="image_metadata.db", help="Path to database file")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    # Set database path
    from web_app import db
    global db
    db = ImageDatabase(args.db)
    
    # Make sure templates and static directories exist
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)
    
    # Get database stats
    try:
        stats = db.get_stats()
        logger.info(f"Starting web app with {stats['total_images']} images in database")
    except Exception as e:
        logger.error(f"Error accessing database: {str(e)}")
        return 1
    
    # Print URL
    url = f"http://{'localhost' if args.host in ['0.0.0.0', '127.0.0.1'] else args.host}:{args.port}"
    print(f"\nWhere's My Photo is running!")
    print(f"Open your browser and navigate to: {url}")
    print("\nPress Ctrl+C to stop the server...\n")
    
    try:
        # Run the application
        app.run(host=args.host, port=args.port, debug=args.debug)
        return 0
    except KeyboardInterrupt:
        print("\nWeb app stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Error running web app: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
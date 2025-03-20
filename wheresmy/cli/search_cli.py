#!/usr/bin/env python3
"""
Command-line interface for searching and retrieving image metadata.

This module provides a simple CLI for searching the image database without 
requiring the web interface. It demonstrates how to use the search_utils and
stats_utils modules.
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, List, Optional, Any

from wheresmy.core.database import ImageDatabase
from wheresmy.search import search as search_utils
from wheresmy.search import stats as stats_utils

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_command_help():
    """Print helpful usage information."""
    print("\nWheresmy Image Search Tool")
    print("=========================")
    print("This tool allows you to search for images using content and context information.")
    print("\nAvailable commands:")
    print("  search  - Search for images by content, date, camera, and other properties")
    print("  stats   - Show database statistics")
    print("  image   - Show detailed information about a specific image by ID")
    print("\nExamples:")
    print("  # Search for all images taken in 2018")
    print("  wheresmy_search search --year 2018")
    print("  # Search for all images taken with Apple devices")
    print("  wheresmy_search search --camera-make Apple")
    print("  # Search for high-resolution images")
    print("  wheresmy_search search --min-width 3000 --min-height 2000")
    print("  # Search by image content (using VLM descriptions)")
    print("  wheresmy_search search --content \"beach sunset\"")
    print("  # Combined search")
    print("  wheresmy_search search --camera-make Apple --year 2018 --content \"cat\"")
    print("  # Show database statistics")
    print("  wheresmy_search stats")
    print("  # Show details for a specific image")
    print("  wheresmy_search image 123")
    print("\nFor complete command details, use: wheresmy_search <command> --help")
    print("")

def main():
    """Main function to parse command-line arguments and execute commands."""
    parser = argparse.ArgumentParser(description="Search and retrieve image metadata")
    parser.add_argument("--db", default="image_metadata.db", help="Path to database file")
    parser.add_argument("--help-examples", action="store_true", help="Show usage examples")
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for images")
    
    # Content search
    content_group = search_parser.add_argument_group("Content Search")
    content_group.add_argument("--query", "-q", help="Text search query (searches descriptions and metadata)")
    content_group.add_argument("--content", help="Search by image content description")
    
    # Context search
    context_group = search_parser.add_argument_group("Context Search")
    context_group.add_argument("--camera-make", help="Filter by camera manufacturer")
    context_group.add_argument("--camera-model", help="Filter by camera model")
    context_group.add_argument("--date-start", help="Filter by start date (YYYY-MM-DD)")
    context_group.add_argument("--date-end", help="Filter by end date (YYYY-MM-DD)")
    context_group.add_argument("--year", type=int, help="Filter by specific year")
    context_group.add_argument("--month", type=int, help="Filter by specific month (1-12)")
    
    # Image properties
    props_group = search_parser.add_argument_group("Image Properties")
    props_group.add_argument("--min-width", type=int, help="Filter by minimum width")
    props_group.add_argument("--min-height", type=int, help="Filter by minimum height")
    props_group.add_argument("--gps", help="Filter by GPS location (latitude,longitude,radius_km)")
    
    # Output options
    output_group = search_parser.add_argument_group("Output Options")
    output_group.add_argument("--limit", type=int, default=10, help="Maximum number of results")
    output_group.add_argument("--offset", type=int, default=0, help="Number of results to skip")
    output_group.add_argument("--sort", choices=["date", "size", "filename"], default="date", 
                          help="Sort results by this field")
    output_group.add_argument("--json", action="store_true", help="Output in JSON format")
    output_group.add_argument("--full-desc", action="store_true", help="Show full descriptions")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    stats_parser.add_argument("--date-interval", choices=["day", "month", "year"], default="month",
                             help="Date grouping interval")
    stats_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    # Image command
    image_parser = subparsers.add_parser("image", help="Show information about a specific image")
    image_parser.add_argument("id", type=int, help="Image ID")
    image_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show usage examples if requested
    if args.help_examples or not args.command:
        print_command_help()
        return 0
    
    # Initialize database
    try:
        db = ImageDatabase(args.db)
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return 1
    
    # Execute command
    if args.command == "search":
        try:
            # Process date arguments
            date_start = args.date_start
            date_end = args.date_end
            
            # Handle year/month arguments
            if args.year:
                if not date_start:
                    date_start = f"{args.year}-01-01"
                if not date_end:
                    date_end = f"{args.year}-12-31"
                    
                # Add month constraint if specified
                if args.month and 1 <= args.month <= 12:
                    month_str = f"{args.month:02d}"
                    date_start = f"{args.year}-{month_str}-01"
                    
                    # Determine last day of month (simplified)
                    last_day = 30
                    if args.month in [1, 3, 5, 7, 8, 10, 12]:
                        last_day = 31
                    elif args.month == 2:
                        last_day = 29 if args.year % 4 == 0 else 28
                    
                    date_end = f"{args.year}-{month_str}-{last_day}"
            
            # Process GPS coordinates if provided
            gps_lat = None
            gps_lon = None
            if args.gps:
                try:
                    parts = args.gps.split(',')
                    if len(parts) >= 2:
                        gps_lat = float(parts[0])
                        gps_lon = float(parts[1])
                except (ValueError, IndexError):
                    logger.warning("Invalid GPS coordinates format. Use latitude,longitude")
            
            # Set up text query - combine query and content arguments
            text_query = args.query
            if args.content:
                if text_query:
                    text_query = f"{text_query} {args.content}"
                else:
                    text_query = args.content
            
            # Execute search
            results = search_utils.search_images(
                db,
                text_query=text_query,
                camera_make=args.camera_make,
                camera_model=args.camera_model,
                date_start=date_start,
                date_end=date_end,
                min_width=args.min_width,
                min_height=args.min_height,
                limit=args.limit,
                offset=args.offset
            )
            
            if args.json:
                print(json.dumps(results, indent=2, default=str))
            else:
                if not results:
                    print("No results found")
                    return 0
                    
                print(f"Found {len(results)} results:")
                for result in results:
                    print(f"\nID: {result.get('id')}")
                    print(f"Filename: {result.get('filename')}")
                    print(f"Path: {result.get('file_path')}")
                    print(f"Size: {result.get('width')}x{result.get('height')}")
                    
                    if result.get("capture_date"):
                        print(f"Date: {result.get('capture_date')}")
                        
                    if result.get("camera_make") or result.get("camera_model"):
                        camera = []
                        if result.get("camera_make"):
                            camera.append(result["camera_make"])
                        if result.get("camera_model"):
                            camera.append(result["camera_model"])
                        print(f"Camera: {' '.join(camera)}")
                    
                    # Show GPS coordinates if available
                    if result.get("gps_lat") and result.get("gps_lon"):
                        print(f"Location: {result.get('gps_lat')}, {result.get('gps_lon')}")
                    
                    # Show content description
                    if result.get("description"):
                        desc = result["description"]
                        if len(desc) > 80 and not args.full_desc:
                            desc = desc[:80] + "..."
                        print(f"Content: {desc}")
                        
            return 0
        except Exception as e:
            logger.error(f"Error performing search: {str(e)}")
            return 1
            
    elif args.command == "stats":
        try:
            statistics = stats_utils.get_all_statistics(db, date_interval=args.date_interval)
            
            if args.json:
                print(json.dumps(statistics, indent=2, default=str))
            else:
                # Display general stats
                stats = statistics["stats"]
                print("Database Statistics:")
                print(f"Total images: {stats['total_images']}")
                print(f"Images with GPS data: {stats['with_gps']}")
                print(f"Images with description: {stats['with_description']}")
                
                # Display top cameras
                print("\nTop Cameras:")
                for i, camera in enumerate(statistics["cameras"][:5], 1):
                    print(f"{i}. {camera['make']} {camera['model']}: {camera['count']} images")
                
                # Display date distribution
                print(f"\nImages by {args.date_interval} (top 5):")
                for i, date_stat in enumerate(statistics["dates"][:5], 1):
                    print(f"{i}. {date_stat['date']}: {date_stat['count']} images")
                    
            return 0
        except Exception as e:
            logger.error(f"Error retrieving statistics: {str(e)}")
            return 1
            
    elif args.command == "image":
        try:
            image = search_utils.get_image_by_id(db, args.id)
            
            if not image:
                print(f"Image with ID {args.id} not found")
                return 1
                
            if args.json:
                print(json.dumps(image, indent=2, default=str))
            else:
                print(f"ID: {image.get('id')}")
                print(f"Filename: {image.get('filename')}")
                print(f"Path: {image.get('file_path')}")
                print(f"Size: {image.get('width')}x{image.get('height')}")
                print(f"Format: {image.get('format')}")
                
                if image.get("capture_date"):
                    print(f"Date: {image.get('capture_date')}")
                    
                if image.get("camera_make") or image.get("camera_model"):
                    camera = []
                    if image.get("camera_make"):
                        camera.append(image["camera_make"])
                    if image.get("camera_model"):
                        camera.append(image["camera_model"])
                    print(f"Camera: {' '.join(camera)}")
                
                if image.get("description"):
                    print(f"\nDescription:")
                    print(image["description"])
                    
                if image.get("gps_lat") and image.get("gps_lon"):
                    print(f"\nGPS: {image['gps_lat']}, {image['gps_lon']}")
                    
            return 0
        except Exception as e:
            logger.error(f"Error retrieving image: {str(e)}")
            return 1
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main())
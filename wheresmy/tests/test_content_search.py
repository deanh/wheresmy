#!/usr/bin/env python3
"""
Content and Context Search Test

This script demonstrates how to use the modularized search functionality 
to search for images based on content (VLM descriptions), time, camera, 
and other contextual information.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from image_database import ImageDatabase
import search_utils
import stats_utils

# Configure logging
logging.basicConfig(level=logging.INFO,
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_date_search(db: ImageDatabase):
    """Test searching for images by date range."""
    logger.info("\n=== Testing Date-based Search ===")
    
    # Get dates from the database stats
    stats = stats_utils.get_database_stats(db)
    date_stats = stats_utils.get_date_statistics(db, interval="year")
    
    if date_stats:
        logger.info(f"Database contains images from these years:")
        for date_stat in date_stats:
            logger.info(f"  {date_stat['date']}: {date_stat['count']} images")
        
        # Search for images from the first year in our data
        first_year = date_stats[0]['date']
        start_date = f"{first_year}-01-01"
        end_date = f"{first_year}-12-31"
        
        logger.info(f"\nSearching for images from {start_date} to {end_date}...")
        results = search_utils.search_images(
            db, 
            date_start=start_date,
            date_end=end_date,
            limit=10
        )
        
        logger.info(f"Found {len(results)} images from {first_year}")
        for i, img in enumerate(results[:3], 1):
            logger.info(f"  {i}. {img.get('filename')} - {img.get('capture_date')}")
    
    else:
        logger.warning("No date statistics available")

def test_camera_search(db: ImageDatabase):
    """Test searching for images by camera make/model."""
    logger.info("\n=== Testing Camera-based Search ===")
    
    # Get camera stats
    camera_stats = stats_utils.get_camera_statistics(db)
    
    if camera_stats:
        logger.info("Available cameras in the database:")
        for i, camera in enumerate(camera_stats, 1):
            logger.info(f"  {i}. {camera['make']} {camera['model']}: {camera['count']} images")
        
        # Use the most common camera for testing
        if camera_stats:
            top_camera = camera_stats[0]
            make = top_camera['make']
            model = top_camera['model']
            
            # Search by camera make
            logger.info(f"\nSearching for images by camera make '{make}'...")
            results = search_utils.search_images(db, camera_make=make, limit=10)
            logger.info(f"Found {len(results)} images with camera make '{make}'")
            
            # Display a few results
            for i, img in enumerate(results[:3], 1):
                logger.info(f"  {i}. {img.get('filename')} - {img.get('camera_make')} {img.get('camera_model')}")
                
            # Search by camera model
            logger.info(f"\nSearching for images by camera model '{model}'...")
            results = search_utils.search_images(db, camera_model=model, limit=10)
            logger.info(f"Found {len(results)} images with camera model '{model}'")
    else:
        logger.warning("No camera statistics available")

def test_dimension_search(db: ImageDatabase):
    """Test searching for images by dimensions."""
    logger.info("\n=== Testing Dimension-based Search ===")
    
    # Get a sample of images
    sample = search_utils.search_images(db, limit=10)
    
    if sample:
        # Find the range of dimensions
        widths = [img.get('width', 0) for img in sample if img.get('width')]
        heights = [img.get('height', 0) for img in sample if img.get('height')]
        
        if widths and heights:
            min_width, max_width = min(widths), max(widths)
            min_height, max_height = min(heights), max(heights)
            
            logger.info(f"Image width range: {min_width} to {max_width} pixels")
            logger.info(f"Image height range: {min_height} to {max_height} pixels")
            
            # Search for larger images
            threshold_width = (min_width + max_width) // 2
            logger.info(f"\nSearching for images with width > {threshold_width}px...")
            results = search_utils.search_images(db, min_width=threshold_width, limit=10)
            logger.info(f"Found {len(results)} images wider than {threshold_width}px")
            
            # Display sample results
            for i, img in enumerate(results[:3], 1):
                logger.info(f"  {i}. {img.get('filename')} - {img.get('width')}x{img.get('height')}")
    else:
        logger.warning("No images found for dimension analysis")

def test_combined_search(db: ImageDatabase):
    """Test combined search criteria."""
    logger.info("\n=== Testing Combined Search Criteria ===")
    
    # Get stats
    camera_stats = stats_utils.get_camera_statistics(db)
    date_stats = stats_utils.get_date_statistics(db, interval="year")
    
    if camera_stats and date_stats and len(date_stats) > 1:
        # Get parameters for search
        camera = camera_stats[0]['make']
        year = date_stats[0]['date']
        
        logger.info(f"Combining criteria: Camera make '{camera}' and year '{year}'")
        
        # Execute search with combined criteria
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        results = search_utils.search_images(
            db,
            camera_make=camera,
            date_start=start_date,
            date_end=end_date,
            limit=10
        )
        
        logger.info(f"Found {len(results)} images matching both criteria")
        
        # Display results
        for i, img in enumerate(results[:3], 1):
            logger.info(f"  {i}. {img.get('filename')} - {img.get('capture_date')} - {img.get('camera_make')}")
    else:
        logger.warning("Insufficient data for combined search test")

def main():
    """Main function to run the tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test content and context-based search")
    parser.add_argument("--db", default="test_search.db", help="Path to database file")
    
    args = parser.parse_args()
    
    # Check if database exists
    if not os.path.exists(args.db):
        logger.error(f"Database file not found: {args.db}")
        return 1
    
    # Initialize database
    try:
        db = ImageDatabase(args.db)
        
        # Get basic stats
        stats = stats_utils.get_database_stats(db)
        logger.info(f"Database contains {stats['total_images']} images")
        
        # Run tests
        test_date_search(db)
        test_camera_search(db)
        test_dimension_search(db)
        test_combined_search(db)
        
        logger.info("\nAll tests completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
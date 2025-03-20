#!/usr/bin/env python3
"""
Search Utilities Module

This module provides utility functions for searching images based on
metadata stored in the database. It abstracts the search functionality
from the web interface for reuse in other contexts.
"""

import logging
from typing import Dict, List, Optional, Any

from image_database import ImageDatabase

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def search_images(
    db: ImageDatabase,
    text_query: Optional[str] = None,
    camera_make: Optional[str] = None,
    camera_model: Optional[str] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    min_width: Optional[int] = None,
    min_height: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Search for images with various filters.
    
    Args:
        db: ImageDatabase instance
        text_query: Optional text to search for
        camera_make: Optional camera manufacturer
        camera_model: Optional camera model
        date_start: Optional start date (ISO format)
        date_end: Optional end date (ISO format)
        min_width: Optional minimum image width
        min_height: Optional minimum image height
        limit: Maximum number of results to return
        offset: Number of results to skip
        
    Returns:
        List of matching image metadata
    """
    try:
        results = db.filter_search(
            text_query=text_query,
            camera_make=camera_make,
            camera_model=camera_model,
            date_start=date_start,
            date_end=date_end,
            min_width=min_width,
            min_height=min_height,
            limit=limit,
            offset=offset
        )
        
        return results
    except Exception as e:
        logger.error(f"Error in search_images: {str(e)}")
        raise

def get_image_by_id(db: ImageDatabase, image_id: int) -> Optional[Dict[str, Any]]:
    """
    Get information about a specific image by ID.
    
    Args:
        db: ImageDatabase instance
        image_id: ID of the image to retrieve
        
    Returns:
        Image metadata or None if not found
    """
    try:
        results = db.filter_search(f"id:{image_id}", limit=1)
        
        if not results:
            return None
            
        return results[0]
    except Exception as e:
        logger.error(f"Error in get_image_by_id: {str(e)}")
        raise
#!/usr/bin/env python3
"""
Statistics Utilities Module

This module provides utility functions for retrieving statistics about
images in the database. It abstracts the statistics functionality
from the web interface for reuse in other contexts.
"""

import logging
from typing import Dict, List, Optional, Any

from image_database import ImageDatabase

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_stats(db: ImageDatabase) -> Dict[str, Any]:
    """
    Get general statistics about the database.
    
    Args:
        db: ImageDatabase instance
        
    Returns:
        Dictionary containing database statistics
    """
    try:
        return db.get_stats()
    except Exception as e:
        logger.error(f"Error in get_database_stats: {str(e)}")
        raise

def get_camera_statistics(db: ImageDatabase) -> List[Dict[str, Any]]:
    """
    Get statistics about cameras used in the collection.
    
    Args:
        db: ImageDatabase instance
        
    Returns:
        List of dictionaries with camera statistics
    """
    try:
        return db.get_camera_stats()
    except Exception as e:
        logger.error(f"Error in get_camera_statistics: {str(e)}")
        raise

def get_date_statistics(db: ImageDatabase, interval: str = "month") -> List[Dict[str, Any]]:
    """
    Get statistics about image dates.
    
    Args:
        db: ImageDatabase instance
        interval: Grouping interval ('year', 'month', or 'day')
        
    Returns:
        List of dictionaries with date statistics
    """
    try:
        return db.get_date_stats(by=interval)
    except Exception as e:
        logger.error(f"Error in get_date_statistics: {str(e)}")
        raise

def get_all_statistics(
    db: ImageDatabase, 
    date_interval: str = "month"
) -> Dict[str, Any]:
    """
    Get all statistics in a single call.
    
    Args:
        db: ImageDatabase instance
        date_interval: Grouping interval for date statistics
        
    Returns:
        Dictionary containing all statistics
    """
    try:
        stats = get_database_stats(db)
        camera_stats = get_camera_statistics(db)
        date_stats = get_date_statistics(db, interval=date_interval)
        
        return {
            "stats": stats,
            "cameras": camera_stats,
            "dates": date_stats
        }
    except Exception as e:
        logger.error(f"Error in get_all_statistics: {str(e)}")
        raise
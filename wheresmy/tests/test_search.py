#!/usr/bin/env python3
"""
Test module for search and statistics utilities.

This module provides simple tests for the search_utils and stats_utils modules,
allowing you to verify that the modularization works correctly without using
the web interface.
"""

import os
import sys

# import json
import logging

# from pathlib import Path

from wheresmy.core.database import ImageDatabase
from wheresmy.search import search as search_utils
from wheresmy.search import stats as stats_utils

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_search(db_path="image_metadata.db"):
    """Test the search functionality."""
    logger.info("Testing search functionality...")

    # Initialize database
    db = ImageDatabase(db_path)

    # Test simple search
    logger.info("Testing simple search...")
    results = search_utils.search_images(db, limit=5)
    logger.info(f"Found {len(results)} results in simple search")

    # Test text search if there are results
    if results:
        # Get a term from the first result's filename or description to search for
        search_term = None

        if results[0].get("filename"):
            search_term = os.path.splitext(results[0]["filename"])[0]
            logger.info(
                f"Testing text search with term '{search_term}' from filename..."
            )
            text_results = search_utils.search_images(
                db, text_query=search_term, limit=5
            )
            logger.info(f"Found {len(text_results)} results in text search")

        # Test image retrieval by ID
        image_id = results[0]["id"]
        logger.info(f"Testing get_image_by_id with ID {image_id}...")
        image_data = search_utils.get_image_by_id(db, image_id)

        if image_data:
            logger.info(f"Successfully retrieved image with ID {image_id}")
        else:
            logger.error(f"Failed to retrieve image with ID {image_id}")

    logger.info("Search tests completed")


def test_stats(db_path="image_metadata.db"):
    """Test the statistics functionality."""
    logger.info("Testing statistics functionality...")

    # Initialize database
    db = ImageDatabase(db_path)

    # Test basic stats
    logger.info("Testing get_database_stats...")
    stats = stats_utils.get_database_stats(db)
    logger.info(f"Database contains {stats['total_images']} images")

    # Test camera stats
    logger.info("Testing get_camera_statistics...")
    camera_stats = stats_utils.get_camera_statistics(db)
    logger.info(f"Found statistics for {len(camera_stats)} different cameras")

    # Test date stats
    logger.info("Testing get_date_statistics...")
    for interval in ["day", "month", "year"]:
        date_stats = stats_utils.get_date_statistics(db, interval=interval)
        logger.info(f"Found {len(date_stats)} date groups when grouping by {interval}")

    # Test combined stats
    logger.info("Testing get_all_statistics...")
    all_stats = stats_utils.get_all_statistics(db)
    if "stats" in all_stats and "cameras" in all_stats and "dates" in all_stats:
        logger.info("Successfully retrieved all statistics")
    else:
        logger.error("Failed to retrieve all statistics")

    logger.info("Statistics tests completed")


def main():
    """Main function to run the tests."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test search and statistics functionality"
    )
    parser.add_argument(
        "--db", default="image_metadata.db", help="Path to database file"
    )
    parser.add_argument(
        "--test",
        choices=["search", "stats", "all"],
        default="all",
        help="Which tests to run",
    )

    args = parser.parse_args()

    # Make sure database exists
    if not os.path.exists(args.db):
        logger.error(f"Database file not found: {args.db}")
        return 1

    # Run selected tests
    if args.test in ["search", "all"]:
        test_search(args.db)

    if args.test in ["stats", "all"]:
        test_stats(args.db)

    logger.info("All tests completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

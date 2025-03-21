"""
Pytest configuration and fixtures for Wheresmy tests.

This module provides shared fixtures for all tests, including a
test database populated with real metadata using production code.
"""

import os
import pytest
import tempfile

# import json
import logging

# from pathlib import Path

from wheresmy.core.database import ImageDatabase
from wheresmy.cli.import_metadata import import_metadata

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def db():
    """
    Create a temporary test database populated with real metadata.

    This fixture:
    1. Creates a temporary database file
    2. Imports the test metadata using the production import code
    3. Returns the database for tests to use
    4. Cleans up after all tests are complete

    Returns:
        An ImageDatabase instance connected to the test database
    """
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    db_path = temp_db.name

    # Get the path to the test metadata file
    test_dir = os.path.dirname(os.path.abspath(__file__))
    metadata_path = os.path.join(
        test_dir, "..", "..", "test_data", "test_metadata.json"
    )
    metadata_path = os.path.normpath(metadata_path)

    # Check if the metadata file exists
    if not os.path.exists(metadata_path):
        pytest.skip(f"Test metadata file not found: {metadata_path}")

    logger.info(f"Creating test database at {db_path}")
    logger.info(f"Importing metadata from {metadata_path}")

    # Import metadata using the production code
    success = import_metadata(metadata_path, db_path, generate_embeddings=True)

    if not success:
        pytest.skip("Failed to import test metadata into the database")

    # Create and return the database instance
    test_db = ImageDatabase(db_path)

    # Check if the database has the expected data
    stats = test_db.get_stats()
    logger.info(f"Test database created with {stats['total_images']} images")

    # Yield the database for tests to use
    yield test_db

    # Clean up after all tests are complete
    try:
        os.unlink(db_path)
        logger.info(f"Removed temporary test database: {db_path}")
    except (OSError, PermissionError) as e:
        logger.warning(f"Failed to remove temporary database {db_path}: {e}")

#!/usr/bin/env python3
"""
Integration Test for Wheresmy Image Search

This script performs an automated end-to-end test of the image search functionality:
1. Extracts metadata from sample images with VLM descriptions
2. Imports the metadata into a test database
3. Runs search queries to validate the functionality
4. Cleans up test artifacts

Usage:
    python integration_test.py [--keep-files] [--sample-dir DIRECTORY]

Options:
    --keep-files    Don't delete test files after running
    --sample-dir    Directory containing sample images (default: sample_directory)
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from image_database import ImageDatabase
import search_utils
import stats_utils

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegrationTest:
    """Class for running the integration test."""
    
    def __init__(self, sample_dir: str = "sample_directory", keep_files: bool = False):
        """
        Initialize the integration test.
        
        Args:
            sample_dir: Directory containing sample images
            keep_files: Whether to keep test files after running
        """
        self.sample_dir = os.path.abspath(sample_dir)
        self.keep_files = keep_files
        
        # Set up test paths
        self.test_dir = tempfile.mkdtemp(prefix="wheresmy_test_")
        self.metadata_file = os.path.join(self.test_dir, "test_metadata.json")
        self.db_file = os.path.join(self.test_dir, "test_search.db")
        
        # Track test results
        self.tests_run = 0
        self.tests_passed = 0
        
    def __del__(self):
        """Clean up test files."""
        if not self.keep_files and os.path.exists(self.test_dir):
            logger.info(f"Cleaning up test directory: {self.test_dir}")
            shutil.rmtree(self.test_dir)
            
    def run_command(self, command: List[str]) -> str:
        """
        Run a command and return its output.
        
        Args:
            command: Command to run as list of strings
            
        Returns:
            Command output
            
        Raises:
            RuntimeError: If command fails
        """
        logger.debug(f"Running command: {' '.join(command)}")
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed with exit code {e.returncode}")
            logger.error(f"STDOUT: {e.stdout}")
            logger.error(f"STDERR: {e.stderr}")
            raise RuntimeError(f"Command failed: {' '.join(command)}")
            
    def extract_metadata(self) -> None:
        """Extract metadata from sample images with VLM descriptions."""
        logger.info("=== Extracting Metadata ===")
        
        # Check if sample directory exists
        if not os.path.exists(self.sample_dir):
            raise FileNotFoundError(f"Sample directory not found: {self.sample_dir}")
            
        # Run metadata extraction with VLM
        logger.info(f"Extracting metadata from {self.sample_dir}")
        self.run_command([
            "python", 
            "image_metadata_extractor.py", 
            "-d", self.sample_dir,
            "-o", self.metadata_file,
            "--vlm", "smolvlm"
        ])
        
        # Verify metadata file was created
        if not os.path.exists(self.metadata_file):
            raise FileNotFoundError(f"Metadata file not created: {self.metadata_file}")
            
        # Check metadata file content
        with open(self.metadata_file, 'r') as f:
            metadata = json.load(f)
            
        image_count = len(metadata)
        logger.info(f"Extracted metadata for {image_count} images")
        
        # Check VLM descriptions
        images_with_vlm = 0
        for img_path, img_data in metadata.items():
            if "vlm_description" in img_data:
                images_with_vlm += 1
                
        logger.info(f"Images with VLM descriptions: {images_with_vlm}/{image_count}")
        
        if images_with_vlm == 0:
            logger.warning("No VLM descriptions found in metadata")
            
        self.assert_true(
            images_with_vlm > 0,
            "At least one image should have a VLM description"
        )
            
    def import_metadata(self) -> None:
        """Import metadata into the test database."""
        logger.info("=== Importing Metadata ===")
        
        # Import metadata into test database
        self.run_command([
            "python",
            "import_metadata.py",
            self.metadata_file,
            "--db", self.db_file
        ])
        
        # Verify database was created
        if not os.path.exists(self.db_file):
            raise FileNotFoundError(f"Database file not created: {self.db_file}")
            
        # Check database contents
        db = ImageDatabase(self.db_file)
        stats = stats_utils.get_database_stats(db)
        
        total_images = stats["total_images"]
        with_descriptions = stats["with_description"]
        
        logger.info(f"Database contains {total_images} images")
        logger.info(f"Images with descriptions: {with_descriptions}")
        
        self.assert_true(
            total_images > 0,
            "Database should contain images"
        )
        self.assert_true(
            with_descriptions > 0,
            "Database should contain images with descriptions"
        )
            
    def run_search_tests(self) -> None:
        """Run search tests to validate functionality."""
        logger.info("=== Testing Search Functionality ===")
        
        db = ImageDatabase(self.db_file)
        
        # Test 1: Basic search
        logger.info("Test 1: Basic search")
        results = search_utils.search_images(db, limit=5)
        self.assert_true(
            len(results) > 0,
            "Basic search should return results"
        )
        
        # Test 2: Content search
        logger.info("Test 2: Content search")
        # Try several keywords that might be in descriptions
        found = False
        for keyword in ["cat", "person", "room", "building", "map", "food", "forest", "table"]:
            results = search_utils.search_images(db, text_query=keyword, limit=5)
            if results:
                logger.info(f"Found {len(results)} results for content search with keyword '{keyword}'")
                found = True
                break
                
        self.assert_true(
            found,
            "Content search should find at least one result with common keywords"
        )
        
        # Test 3: Combined search
        logger.info("Test 3: Combined search with content and camera make")
        
        # Get camera stats
        camera_stats = stats_utils.get_camera_statistics(db)
        if camera_stats:
            camera_make = camera_stats[0]["make"]
            logger.info(f"Using camera make '{camera_make}' for combined search")
            
            # Try several keywords with camera make
            found = False
            for keyword in ["cat", "person", "room", "building", "map", "food", "forest", "table"]:
                results = search_utils.search_images(
                    db, 
                    text_query=keyword,
                    camera_make=camera_make,
                    limit=5
                )
                if results:
                    logger.info(f"Found {len(results)} results for combined search with keyword '{keyword}' and camera '{camera_make}'")
                    found = True
                    break
                    
            self.assert_true(
                found,
                "Combined search should find at least one result"
            )
        else:
            logger.warning("No camera statistics found, skipping combined search test")
            
        # Test 4: Date search
        logger.info("Test 4: Date search")
        
        # Get date stats
        date_stats = stats_utils.get_date_statistics(db, interval="year")
        if date_stats:
            year = date_stats[0]["date"]
            logger.info(f"Using year '{year}' for date search")
            
            # Search by year
            results = search_utils.search_images(
                db,
                date_start=f"{year}-01-01",
                date_end=f"{year}-12-31",
                limit=5
            )
            
            self.assert_true(
                len(results) > 0,
                f"Date search for year {year} should return results"
            )
            
            if results:
                logger.info(f"Found {len(results)} results for date search with year '{year}'")
        else:
            logger.warning("No date statistics found, skipping date search test")
            
        # Test 5: CLI search interface
        logger.info("Test 5: CLI search interface")
        output = self.run_command([
            "python",
            "search_cli.py",
            "--db", self.db_file,
            "search",
            "--limit", "3"
        ])
        
        self.assert_true(
            "Found" in output and "results" in output,
            "CLI search should return formatted results"
        )
        
    def assert_true(self, condition: bool, message: str) -> None:
        """
        Assert that a condition is true.
        
        Args:
            condition: Condition to check
            message: Message to display on failure
        """
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            logger.info(f"✓ PASS: {message}")
        else:
            logger.error(f"✗ FAIL: {message}")
            
    def run(self) -> bool:
        """
        Run the integration test.
        
        Returns:
            True if all tests passed, False otherwise
        """
        logger.info(f"Starting integration test with sample directory: {self.sample_dir}")
        logger.info(f"Test files will be stored in: {self.test_dir}")
        
        try:
            # Run test stages
            self.extract_metadata()
            self.import_metadata()
            self.run_search_tests()
            
            # Report results
            logger.info("=== Test Results ===")
            logger.info(f"Tests run: {self.tests_run}")
            logger.info(f"Tests passed: {self.tests_passed}")
            
            success = self.tests_run == self.tests_passed
            if success:
                logger.info("✓ All tests passed!")
            else:
                logger.error(f"✗ {self.tests_run - self.tests_passed} tests failed")
                
            return success
            
        except Exception as e:
            logger.error(f"Integration test failed with error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

def main():
    """Main function to run the integration test."""
    parser = argparse.ArgumentParser(description="Run integration test for image search")
    parser.add_argument("--keep-files", action="store_true", help="Don't delete test files after running")
    parser.add_argument("--sample-dir", default="sample_directory", help="Directory containing sample images")
    
    args = parser.parse_args()
    
    # Run integration test
    test = IntegrationTest(args.sample_dir, args.keep_files)
    success = test.run()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
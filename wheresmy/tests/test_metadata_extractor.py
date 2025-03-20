"""
Unit tests for the image metadata extractor.
"""

import os
import unittest
import json
import tempfile
from unittest.mock import MagicMock, patch
from PIL import Image

# Import the modules to test
# Import the VLM describer
from wheresmy.core.vlm_describers import BaseVLMDescriber


class MockVLMDescriber(BaseVLMDescriber):
    """A mock VLM describer for testing."""
    
    def initialize_model(self):
        """Mock initialization."""
        self.model = MagicMock()
        self.processor = MagicMock()
    
    def generate_description(self, image_path, prompt=None):
        """Return a mock description."""
        return {
            "description": "This is a mock description of an image.",
            "model": "MockVLM",
            "processing_time": 0.1,
            "prompt": prompt or "Default prompt"
        }


# Import the main module functions after we've set up the mock
from image_metadata_extractor import extract_metadata, process_directory


class TestMetadataExtractor(unittest.TestCase):
    """Test the image-metadata-extractor functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary image for testing
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        self.temp_file.close()
        
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        img.save(self.temp_file.name)
        
        # Create a temporary directory for directory tests
        self.temp_dir = tempfile.TemporaryDirectory()
        # Create a few images in the temp directory
        for i in range(3):
            img_path = os.path.join(self.temp_dir.name, f'test_img_{i}.jpg')
            img.save(img_path)
        
        # Initialize the mock VLM describer
        self.mock_vlm = MockVLMDescriber()
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove the temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
        
        # Close and remove the temporary directory
        self.temp_dir.cleanup()
    
    def test_extract_metadata_basic(self):
        """Test basic metadata extraction without VLM."""
        # Extract metadata without VLM
        metadata = extract_metadata(self.temp_file.name)
        
        # Check basic fields
        self.assertIn("filename", metadata)
        self.assertIn("format", metadata)
        self.assertIn("mode", metadata)
        self.assertIn("size", metadata)
        self.assertIn("width", metadata)
        self.assertIn("height", metadata)
        
        # Check specific values
        self.assertEqual(metadata["format"], "JPEG")
        self.assertEqual(metadata["width"], 100)
        self.assertEqual(metadata["height"], 100)
    
    def test_extract_metadata_with_vlm(self):
        """Test metadata extraction with VLM integration."""
        # Extract metadata with mock VLM
        metadata = extract_metadata(self.temp_file.name, vlm_describer=self.mock_vlm)
        
        # Check VLM description
        self.assertIn("vlm_description", metadata)
        vlm_desc = metadata["vlm_description"]
        
        # Check description fields
        self.assertIn("description", vlm_desc)
        self.assertIn("model", vlm_desc)
        self.assertIn("processing_time", vlm_desc)
        self.assertIn("prompt", vlm_desc)
        
        # Check values
        self.assertEqual(vlm_desc["model"], "MockVLM")
        self.assertEqual(vlm_desc["description"], "This is a mock description of an image.")
    
    def test_extract_metadata_with_custom_prompt(self):
        """Test metadata extraction with custom VLM prompt."""
        custom_prompt = "Describe this image with a focus on colors."
        metadata = extract_metadata(
            self.temp_file.name, 
            vlm_describer=self.mock_vlm,
            vlm_prompt=custom_prompt
        )
        
        # Check the prompt was passed through
        self.assertEqual(
            metadata["vlm_description"]["prompt"],
            custom_prompt
        )
    
    def test_process_directory(self):
        """Test processing a directory of images."""
        # Process directory with mock VLM
        results = process_directory(
            self.temp_dir.name,
            vlm_describer=self.mock_vlm
        )
        
        # Check we have results for each image
        self.assertEqual(len(results), 3)
        
        # Check each result has the expected structure
        for file_path, metadata in results.items():
            self.assertTrue(file_path.startswith(self.temp_dir.name))
            self.assertIn("vlm_description", metadata)
            self.assertIn("description", metadata["vlm_description"])
    
    def test_vlm_error_handling(self):
        """Test error handling for VLM description generation."""
        # Create a VLM describer that raises an exception
        class ErrorVLMDescriber(BaseVLMDescriber):
            def initialize_model(self):
                self._is_initialized = True
                
            def generate_description(self, image_path, prompt=None):
                raise Exception("VLM error")
        
        error_vlm = ErrorVLMDescriber()
        
        # Run extraction - should not crash despite the VLM error
        metadata = extract_metadata(self.temp_file.name, vlm_describer=error_vlm)
        
        # Check error field exists
        self.assertIn("vlm_description_error", metadata)
        self.assertIn("VLM error", metadata["vlm_description_error"])
    
    def test_nonexistent_file(self):
        """Test handling of nonexistent files."""
        # Try to extract metadata from a nonexistent file
        metadata = extract_metadata("/nonexistent/path.jpg")
        
        # Check error field
        self.assertIn("error", metadata)
        self.assertIn("File not found", metadata["error"])


if __name__ == '__main__':
    unittest.main()
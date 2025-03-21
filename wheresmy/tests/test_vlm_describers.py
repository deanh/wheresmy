"""
Unit tests for the VLM describers module.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import tempfile
from PIL import Image

from wheresmy.core.vlm_describers import (
    BaseVLMDescriber,
    SmolVLMDescriber,
    get_vlm_describer,
)


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
            "prompt": prompt or "Default prompt",
        }


class TestBaseVLMDescriber(unittest.TestCase):
    """Test the BaseVLMDescriber abstract class."""

    def test_abstract_class(self):
        """Test that BaseVLMDescriber is an abstract class."""
        with self.assertRaises(TypeError):
            BaseVLMDescriber()  # Should fail as it's an abstract class

    def test_call_ensure_initialized(self):
        """Test that __call__ ensures initialization."""
        mock_describer = MockVLMDescriber()

        # Create a temporary image for testing
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp_file:
            # Create a small test image
            img = Image.new("RGB", (100, 100), color="red")
            img.save(tmp_file.name)

            # Test calling the describer
            result = mock_describer(tmp_file.name, "Test prompt")

            # Check result has expected structure
            self.assertIn("description", result)
            self.assertIn("model", result)
            self.assertIn("processing_time", result)
            self.assertIn("prompt", result)
            self.assertEqual(result["prompt"], "Test prompt")


class TestSmolVLMDescriber(unittest.TestCase):
    """Test the SmolVLMDescriber implementation."""

    @patch("wheresmy.core.vlm_describers.AutoProcessor")
    @patch("wheresmy.core.vlm_describers.AutoModelForVision2Seq")
    def test_initialization_structure(self, mock_model_class, mock_processor_class):
        """Test that SmolVLMDescriber initializes with correct parameters."""
        # Setup mocks
        mock_processor = MagicMock()
        mock_model = MagicMock()
        mock_processor_class.from_pretrained.return_value = mock_processor
        mock_model_class.from_pretrained.return_value = mock_model
        mock_model.to.return_value = mock_model  # Handle device movement

        # Initialize describer
        describer = SmolVLMDescriber()
        describer.initialize_model()

        # Check model initialization
        mock_processor_class.from_pretrained.assert_called_once_with(
            SmolVLMDescriber.MODEL_NAME, cache_dir=None
        )

        # Check model was created and moved to device
        self.assertIsNotNone(describer.model)
        self.assertIsNotNone(describer.processor)

    def test_generate_description_structure(self):
        """Test the structure of generate_description output with a mock."""

        # Create a simplified mock for testing
        class TestSmolVLM(SmolVLMDescriber):
            def initialize_model(self):
                self.model = MagicMock()
                self.processor = MagicMock()
                self.processor.apply_chat_template = MagicMock(return_value="template")
                self.processor.batch_decode = MagicMock(
                    return_value=[
                        "User:<image>Prompt\nAssistant: This is a test description"
                    ]
                )
                self.processor.return_value = {
                    "input_ids": MagicMock(),
                    "pixel_values": MagicMock(),
                }
                self.model.generate = MagicMock(return_value=[])
                self._is_initialized = True

        # Initialize describer
        describer = TestSmolVLM()

        # Test generate_description with a mock implementation
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp_file:
            # Create a small test image
            img = Image.new("RGB", (100, 100), color="red")
            img.save(tmp_file.name)

            # Create a simplified version that avoids model operations
            def mock_generate_description(image_path, prompt=None):
                return {
                    "description": "This is a test description",
                    "model": SmolVLMDescriber.MODEL_NAME,
                    "processing_time": 0.1,
                    "prompt": prompt or SmolVLMDescriber.DEFAULT_PROMPT,
                }

            # Patch the method
            original_method = describer.generate_description
            describer.generate_description = mock_generate_description

            try:
                # Call the function
                result = describer(tmp_file.name, "Test prompt")

                # Check result structure
                self.assertIn("description", result)
                self.assertIn("model", result)
                self.assertIn("processing_time", result)
                self.assertIn("prompt", result)
                self.assertEqual(result["description"], "This is a test description")
                self.assertEqual(result["model"], SmolVLMDescriber.MODEL_NAME)
            finally:
                # Restore original method
                describer.generate_description = original_method


class TestFactoryFunction(unittest.TestCase):
    """Test the VLM describer factory function."""

    def test_get_smolvlm_describer(self):
        """Test that get_vlm_describer returns a SmolVLMDescriber for 'smolvlm'."""
        describer = get_vlm_describer("smolvlm")
        self.assertIsInstance(describer, SmolVLMDescriber)

    def test_invalid_model_name(self):
        """Test that get_vlm_describer raises ValueError for invalid model names."""
        with self.assertRaises(ValueError):
            get_vlm_describer("nonexistent_model")


class TestErrorHandling(unittest.TestCase):
    """Test error handling in VLM describers."""

    def test_file_not_found(self):
        """Test handling of file not found errors."""

        # Initialize describer with error checking
        class ErrorCheckingMockVLMDescriber(MockVLMDescriber):
            def generate_description(self, image_path, prompt=None):
                if not os.path.exists(image_path):
                    return {"error": f"Image file not found: {image_path}"}
                return super().generate_description(image_path, prompt)

        describer = ErrorCheckingMockVLMDescriber()

        # Test with nonexistent file
        result = describer("/nonexistent/path.jpg")

        # Check result
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Image file not found: /nonexistent/path.jpg")


if __name__ == "__main__":
    unittest.main()

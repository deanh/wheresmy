"""
Unit tests for the text embeddings generator module.
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import json


class MockEmbeddingModel:
    """A mock sentence transformer model for testing."""
    
    def __init__(self):
        """Initialize the mock model."""
        pass
    
    def encode(self, texts, **kwargs):
        """Return mock embeddings for testing."""
        if isinstance(texts, str):
            # Return a consistent mock embedding for a single text
            # Use hash of the text to generate a unique pattern
            seed = abs(hash(texts)) % 100
            return np.ones(384) * (seed / 100.0) + np.arange(384) * (seed / 10000.0)
        else:
            # Return mock embeddings for a list of texts
            # Use the hash of each text to create different vectors
            embeddings = []
            for text in texts:
                seed = abs(hash(text)) % 100
                embedding = np.ones(384) * (seed / 100.0) + np.arange(384) * (seed / 10000.0)
                embeddings.append(embedding)
            return np.array(embeddings)


class TestTextEmbeddingGenerator(unittest.TestCase):
    """Test the TextEmbeddingGenerator class."""
    
    @patch('wheresmy.core.text_embeddings.SentenceTransformer')
    def test_initialization(self, mock_sentence_transformer):
        """Test that TextEmbeddingGenerator initializes correctly."""
        from wheresmy.core.text_embeddings import TextEmbeddingGenerator
        
        # Setup mock
        mock_model = MagicMock()
        mock_sentence_transformer.return_value = mock_model
        
        # Initialize generator
        generator = TextEmbeddingGenerator()
        
        # Verify model initialization with correct parameters
        mock_sentence_transformer.assert_called_once_with(
            TextEmbeddingGenerator.DEFAULT_MODEL_NAME
        )
        
        # Check model was loaded
        self.assertIsNotNone(generator.model)
    
    @patch('wheresmy.core.text_embeddings.SentenceTransformer', return_value=MockEmbeddingModel())
    def test_generate_embedding_structure(self, mock_sentence_transformer):
        """Test the structure of generate_embedding output."""
        from wheresmy.core.text_embeddings import TextEmbeddingGenerator
        
        # Initialize generator
        generator = TextEmbeddingGenerator()
        
        # Test with a single text
        text = "This is a test description of an image showing a sunset."
        result = generator.generate_embedding(text)
        
        # Check result structure
        self.assertIsInstance(result, dict)
        self.assertIn("embedding", result)
        self.assertIn("model", result)
        self.assertIn("text", result)
        self.assertIn("embedding_size", result)
        
        # Check embedding is a numpy array with expected size
        self.assertIsInstance(result["embedding"], np.ndarray)
        self.assertEqual(len(result["embedding"]), 384)  # all-MiniLM-L6-v2 has 384 dimensions
        self.assertEqual(result["embedding_size"], 384)
        self.assertEqual(result["text"], text)
        self.assertEqual(result["model"], TextEmbeddingGenerator.DEFAULT_MODEL_NAME)
    
    @patch('wheresmy.core.text_embeddings.SentenceTransformer', return_value=MockEmbeddingModel())
    def test_generate_embeddings_batch(self, mock_sentence_transformer):
        """Test generating embeddings for multiple texts at once."""
        from wheresmy.core.text_embeddings import TextEmbeddingGenerator
        
        # Initialize generator
        generator = TextEmbeddingGenerator()
        
        # Test with multiple texts
        texts = [
            "A serene landscape with mountains in the background.",
            "A busy street in a city with people walking.",
            "A close-up of a flower with a bee collecting pollen."
        ]
        
        results = generator.generate_embeddings(texts)
        
        # Check results structure
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), len(texts))
        
        for i, result in enumerate(results):
            self.assertIsInstance(result, dict)
            self.assertIn("embedding", result)
            self.assertIn("model", result)
            self.assertIn("text", result)
            self.assertIn("embedding_size", result)
            
            # Check embedding is a numpy array with expected size
            self.assertIsInstance(result["embedding"], np.ndarray)
            self.assertEqual(len(result["embedding"]), 384)
            self.assertEqual(result["embedding_size"], 384)
            self.assertEqual(result["text"], texts[i])
            self.assertEqual(result["model"], TextEmbeddingGenerator.DEFAULT_MODEL_NAME)
            
            # Ensure each text gets a different embedding
            if i > 0:
                self.assertFalse(np.array_equal(result["embedding"], results[0]["embedding"]))
    
    @patch('wheresmy.core.text_embeddings.SentenceTransformer', return_value=MockEmbeddingModel())
    def test_query_embedding(self, mock_sentence_transformer):
        """Test generating a search query embedding."""
        from wheresmy.core.text_embeddings import TextEmbeddingGenerator
        
        # Initialize generator
        generator = TextEmbeddingGenerator()
        
        # Test with a search query
        query = "sunset over mountains"
        result = generator.generate_query_embedding(query)
        
        # Check result structure - should be same as regular embedding
        self.assertIsInstance(result, dict)
        self.assertIn("embedding", result)
        self.assertIn("model", result)
        self.assertIn("text", result)
        self.assertIn("embedding_size", result)
        self.assertEqual(result["text"], query)
    
    @patch('wheresmy.core.text_embeddings.SentenceTransformer', return_value=MagicMock())
    def test_error_handling(self, mock_sentence_transformer):
        """Test error handling in embedding generation."""
        from wheresmy.core.text_embeddings import TextEmbeddingGenerator
        
        # Setup mock to raise an exception when encode is called
        mock_model = mock_sentence_transformer.return_value
        mock_model.encode.side_effect = Exception("Test error")
        
        # Initialize generator
        generator = TextEmbeddingGenerator()
        
        # Test error handling
        result = generator.generate_embedding("Test text")
        
        # Check result has error field
        self.assertIn("error", result)
        self.assertNotIn("embedding", result)
    
    @patch('wheresmy.core.text_embeddings.SentenceTransformer', return_value=MockEmbeddingModel())
    def test_custom_model_name(self, mock_sentence_transformer):
        """Test initialization with custom model name."""
        from wheresmy.core.text_embeddings import TextEmbeddingGenerator
        
        # Custom model name
        custom_model = "custom/model-name"
        
        # Initialize generator with custom model
        generator = TextEmbeddingGenerator(model_name=custom_model)
        
        # Verify model initialization with custom parameters
        mock_sentence_transformer.assert_called_once_with(custom_model)
        
        # Check model was stored
        self.assertEqual(generator.model_name, custom_model)
    
    @patch('wheresmy.core.text_embeddings.SentenceTransformer', return_value=MockEmbeddingModel())
    def test_embedding_serialization(self, mock_sentence_transformer):
        """Test that embeddings can be properly serialized to JSON."""
        from wheresmy.core.text_embeddings import TextEmbeddingGenerator
        
        # Initialize generator
        generator = TextEmbeddingGenerator()
        
        # Generate an embedding
        text = "This is a test description."
        result = generator.generate_embedding(text)
        
        # Try to serialize the embedding to JSON
        try:
            # Convert numpy array to list for JSON serialization
            result_serializable = result.copy()
            result_serializable["embedding"] = result["embedding"].tolist()
            
            # Attempt to serialize
            json_str = json.dumps(result_serializable)
            self.assertIsInstance(json_str, str)
            
            # Verify we can deserialize it back
            deserialized = json.loads(json_str)
            self.assertIsInstance(deserialized["embedding"], list)
            self.assertEqual(len(deserialized["embedding"]), 384)
        except Exception as e:
            self.fail(f"Serialization failed: {e}")


if __name__ == '__main__':
    unittest.main()
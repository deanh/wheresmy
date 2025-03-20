"""
Text Embedding Generator - Create and manage text embeddings for semantic search.

This module provides functionality to generate vector embeddings from text descriptions
using Sentence Transformers, specifically designed to work with VLM-generated 
image descriptions for semantic search capabilities.
"""

import time
import logging
from typing import Dict, List, Any, Union, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class TextEmbeddingGenerator:
    """Generate text embeddings for semantic search using Sentence Transformers."""
    
    # Default model to use for embeddings (all-MiniLM-L6-v2 with 384 dimensions)
    DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
    
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize the text embedding generator.
        
        Args:
            model_name: Name of the sentence-transformers model to use
                       (default: all-MiniLM-L6-v2)
            device: Device to run inference on ('cuda', 'cpu', etc.).
                   If None, will auto-detect.
        """
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.device = device
        
        # Initialize the model
        logger.info(f"Initializing text embedding model: {self.model_name}")
        try:
            start_time = time.time()
            self.model = SentenceTransformer(self.model_name)
            
            # Move to specified device if provided
            if self.device:
                self.model = self.model.to(self.device)
                
            logger.info(f"Model initialized in {time.time() - start_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Error initializing embedding model: {str(e)}")
            raise
    
    def generate_embedding(self, text: str) -> Dict[str, Any]:
        """
        Generate an embedding for a single text string.
        
        Args:
            text: The text to generate an embedding for
            
        Returns:
            Dictionary containing the embedding vector and metadata
        """
        if not text or not isinstance(text, str):
            return {
                "error": "Text must be a non-empty string",
                "model": self.model_name
            }
        
        try:
            logger.debug(f"Generating embedding for text: {text[:50]}...")
            start_time = time.time()
            
            # Generate the embedding
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Return the result
            result = {
                "embedding": embedding,
                "embedding_size": len(embedding),
                "text": text,
                "model": self.model_name,
                "processing_time": time.time() - start_time
            }
            
            logger.debug(f"Embedding generated in {result['processing_time']:.4f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return {
                "error": f"Error generating embedding: {str(e)}",
                "model": self.model_name,
                "text": text
            }
    
    def generate_embeddings(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of text strings to generate embeddings for
            
        Returns:
            List of dictionaries containing the embedding vectors and metadata
        """
        if not texts:
            return []
        
        try:
            logger.info(f"Generating batch embeddings for {len(texts)} texts")
            start_time = time.time()
            
            # Generate embeddings for all texts at once (more efficient)
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            
            # Create result dictionaries for each embedding
            results = []
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                results.append({
                    "embedding": embedding,
                    "embedding_size": len(embedding),
                    "text": text,
                    "model": self.model_name,
                    "processing_time": (time.time() - start_time) / len(texts)  # Approximate per-item time
                })
            
            logger.info(f"Batch embeddings generated in {time.time() - start_time:.2f} seconds")
            return results
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            # Return error dictionaries for each text
            return [
                {
                    "error": f"Error generating batch embeddings: {str(e)}",
                    "model": self.model_name,
                    "text": text
                }
                for text in texts
            ]
    
    def generate_query_embedding(self, query: str) -> Dict[str, Any]:
        """
        Generate an embedding for a search query.
        This is a wrapper around generate_embedding that may apply
        different processing for queries vs. document embeddings.
        
        Args:
            query: The search query text
            
        Returns:
            Dictionary containing the embedding vector and metadata
        """
        # Currently, we process queries the same way as documents
        # In the future, we might add query-specific processing
        return self.generate_embedding(query)


# Example usage
if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python text_embeddings.py <text> [model_name]")
        sys.exit(1)
    
    text = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Initialize generator
    generator = TextEmbeddingGenerator(model_name)
    
    # Generate and print embedding
    result = generator.generate_embedding(text)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    
    print(f"Model: {result['model']}")
    print(f"Embedding size: {result['embedding_size']}")
    print(f"Processing time: {result['processing_time']:.4f} seconds")
    
    # Print a few values from the embedding
    embedding = result["embedding"]
    preview = ", ".join([f"{x:.6f}" for x in embedding[:5]])
    print(f"Embedding preview: [{preview}, ...]")
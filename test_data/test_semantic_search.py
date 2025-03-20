#!/usr/bin/env python3
"""
Test script for semantic search functionality.
"""

import os
import sys
import numpy as np
from pathlib import Path

# Add the parent directory to sys.path to find the wheresmy module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wheresmy.core.database import ImageDatabase
from wheresmy.core.text_embeddings import TextEmbeddingGenerator

# Initialize the database
db = ImageDatabase("test_data/test_embeddings.db")

# Initialize the embedding generator
embedder = TextEmbeddingGenerator()
print(f"Using embedding model: {embedder.model_name}")

# Generate an embedding for a search query
query = "sunset over mountains"
query_embedding = embedder.generate_embedding(query)
print(f"Generated query embedding with size: {query_embedding['embedding_size']}")

# Perform a semantic search
results = db.semantic_search(query_embedding["embedding"])
print(f"Found {len(results)} semantic search results")

# Print the results with similarity scores
for i, result in enumerate(results):
    print(f"Result {i+1}:")
    print(f"  Image: {result['filename']}")
    print(f"  Similarity: {result['similarity']:.4f}")
    print(f"  Description: {result.get('description', 'N/A')}")
    print()

# Try a hybrid search
hybrid_results = db.hybrid_search(query, query_embedding["embedding"])
print(f"Found {len(hybrid_results)} hybrid search results")

# Print the hybrid results
for i, result in enumerate(hybrid_results):
    print(f"Hybrid Result {i+1}:")
    print(f"  Image: {result['filename']}")
    print(f"  Combined Score: {result.get('combined_score', 0):.4f}")
    print(f"  Similarity: {result.get('similarity', 0):.4f}")
    print()

print("Test completed successfully!")
#!/usr/bin/env python3
"""
Search Utilities Module

This module provides utility functions for searching images based on
metadata stored in the database. It abstracts the search functionality
from the web interface for reuse in other contexts, including:
- Text-based search using full-text database capabilities
- Semantic search using vector embeddings
- Hybrid search combining text and semantic approaches
"""

import logging

# import numpy as np
from typing import Dict, List, Optional, Any

from wheresmy.core.database import ImageDatabase
from wheresmy.core.text_embeddings import TextEmbeddingGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
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
    offset: int = 0,
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
            offset=offset,
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


def semantic_search(
    db: ImageDatabase,
    query: str,
    embedding_model: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Search for images using semantic similarity to the query text.

    Args:
        db: ImageDatabase instance
        query: Text query to search for semantically similar images
        embedding_model: Optional name of embedding model to use
        limit: Maximum number of results to return

    Returns:
        List of matching image metadata with similarity scores
    """
    try:
        # Initialize embedding generator
        embedding_generator = TextEmbeddingGenerator(model_name=embedding_model)

        # Generate embedding for the query
        logger.info(f"Generating embedding for query: '{query}'")
        query_embedding_result = embedding_generator.generate_query_embedding(query)

        if "error" in query_embedding_result:
            logger.error(
                f"Error generating query embedding: {query_embedding_result['error']}"
            )
            return []

        # Get the actual embedding vector
        query_embedding = query_embedding_result["embedding"]

        # Perform semantic search
        logger.info(
            f"Performing semantic search with query embedding size: {len(query_embedding)}"
        )
        results = db.semantic_search(query_embedding, limit=limit)

        return results
    except Exception as e:
        logger.error(f"Error in semantic_search: {str(e)}")
        return []


def hybrid_search(
    db: ImageDatabase,
    query: str,
    embedding_model: Optional[str] = None,
    text_weight: float = 0.5,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Search for images using both text search and semantic similarity.

    Args:
        db: ImageDatabase instance
        query: Text query for both text search and semantic embedding
        embedding_model: Optional name of embedding model to use
        text_weight: Weight for text search results (0.0 to 1.0)
        limit: Maximum number of results to return

    Returns:
        List of matching image metadata with combined scores
    """
    try:
        # Initialize embedding generator
        embedding_generator = TextEmbeddingGenerator(model_name=embedding_model)

        # Generate embedding for the query
        logger.info(f"Generating embedding for hybrid query: '{query}'")
        query_embedding_result = embedding_generator.generate_query_embedding(query)

        if "error" in query_embedding_result:
            logger.error(
                f"Error generating query embedding: {query_embedding_result['error']}"
            )
            # Fallback to regular text search
            logger.info("Falling back to regular text search")
            return search_images(db, text_query=query, limit=limit)

        # Get the actual embedding vector
        query_embedding = query_embedding_result["embedding"]

        # Perform hybrid search
        logger.info(f"Performing hybrid search with text weight: {text_weight}")
        results = db.hybrid_search(
            query, query_embedding, limit=limit, text_weight=text_weight
        )

        return results
    except Exception as e:
        logger.error(f"Error in hybrid_search: {str(e)}")
        # Fallback to regular text search
        logger.info("Falling back to regular text search due to error")
        try:
            return search_images(db, text_query=query, limit=limit)
        except Exception:
            return []

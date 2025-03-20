#!/usr/bin/env python3
"""
Image Database Module

This module provides functionality to store and search image metadata.
It uses SQLite as the database backend and provides full-text search
capabilities for image metadata.
"""

import os
import json
import logging
import sqlite3
import time
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DB_VERSION = 2
CREATE_IMAGES_TABLE = """
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    format TEXT,
    width INTEGER,
    height INTEGER,
    exif TEXT,
    gps_lat REAL,
    gps_lon REAL,
    capture_date TEXT,
    camera_make TEXT,
    camera_model TEXT,
    description TEXT,
    description_model TEXT,
    thumbnail TEXT,
    added_date TEXT NOT NULL,
    last_modified TEXT NOT NULL,
    metadata BLOB
);
"""

CREATE_EMBEDDINGS_TABLE = """
CREATE TABLE IF NOT EXISTS text_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    model_name TEXT NOT NULL,
    embedding_size INTEGER NOT NULL,
    embedding BLOB NOT NULL,
    added_date TEXT NOT NULL,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);
"""

# Index on the image_id for quick lookups of embeddings by image
CREATE_EMBEDDING_INDEX = """
CREATE INDEX IF NOT EXISTS idx_embedding_image_id ON text_embeddings(image_id);
"""

CREATE_SEARCH_INDEX = """
CREATE VIRTUAL TABLE IF NOT EXISTS image_search 
USING fts5(
    id, 
    filename, 
    description, 
    camera_make, 
    camera_model, 
    content='images', 
    content_rowid='id',
    tokenize='porter unicode61'
);
"""

CREATE_TRIGGER_INSERT = """
CREATE TRIGGER IF NOT EXISTS image_insert_trigger 
AFTER INSERT ON images
BEGIN
    INSERT INTO image_search(rowid, filename, description, camera_make, camera_model)
    VALUES (new.id, new.filename, new.description, new.camera_make, new.camera_model);
END;
"""

CREATE_TRIGGER_UPDATE = """
CREATE TRIGGER IF NOT EXISTS image_update_trigger 
AFTER UPDATE ON images
BEGIN
    UPDATE image_search 
    SET filename = new.filename, 
        description = new.description,
        camera_make = new.camera_make,
        camera_model = new.camera_model
    WHERE rowid = new.id;
END;
"""

CREATE_TRIGGER_DELETE = """
CREATE TRIGGER IF NOT EXISTS image_delete_trigger 
AFTER DELETE ON images
BEGIN
    DELETE FROM image_search WHERE rowid = old.id;
END;
"""

class ImageDatabase:
    """Database for storing and searching image metadata."""
    
    def __init__(self, db_path: str = "image_metadata.db"):
        """
        Initialize the database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._initialize_db()
        
    def _initialize_db(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # Create version table
            cursor.execute("CREATE TABLE IF NOT EXISTS db_version (version INTEGER);")
            cursor.execute("SELECT version FROM db_version")
            result = cursor.fetchone()
            
            if not result:
                # New database, initialize
                cursor.execute("INSERT INTO db_version VALUES (?)", (DB_VERSION,))
                
                # Create tables and indexes
                cursor.execute(CREATE_IMAGES_TABLE)
                cursor.execute(CREATE_SEARCH_INDEX)
                cursor.execute(CREATE_TRIGGER_INSERT)
                cursor.execute(CREATE_TRIGGER_UPDATE)
                cursor.execute(CREATE_TRIGGER_DELETE)
                cursor.execute(CREATE_EMBEDDINGS_TABLE)
                cursor.execute(CREATE_EMBEDDING_INDEX)
                
                # Create indexes for common search fields
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_capture_date ON images(capture_date);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera ON images(camera_make, camera_model);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_gps ON images(gps_lat, gps_lon);")
                
                conn.commit()
                logger.info(f"Initialized new database at {self.db_path}")
            else:
                current_version = result[0]
                if current_version < DB_VERSION:
                    # Perform schema migrations
                    logger.info(f"Upgrading database from version {current_version} to {DB_VERSION}")
                    
                    # Version 1 to 2: Add text embeddings support
                    if current_version == 1 and DB_VERSION >= 2:
                        logger.info("Upgrading database schema: Adding text embeddings tables")
                        cursor.execute(CREATE_EMBEDDINGS_TABLE)
                        cursor.execute(CREATE_EMBEDDING_INDEX)
                    
                    # Update version
                    cursor.execute("UPDATE db_version SET version = ?", (DB_VERSION,))
                    conn.commit()
                    logger.info(f"Database upgraded to version {DB_VERSION}")
                    
        finally:
            conn.close()
            
    def add_image(self, metadata: Dict[str, Any]) -> int:
        """
        Add an image to the database.
        
        Args:
            metadata: Dictionary containing image metadata
            
        Returns:
            ID of the inserted row
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # Extract commonly queried fields
        file_path = metadata.get("file_path", "")
        filename = metadata.get("filename", os.path.basename(file_path))
        img_format = metadata.get("format", "")
        width = metadata.get("width", 0)
        height = metadata.get("height", 0)
        
        # Extract GPS coordinates
        gps_lat = None
        gps_lon = None
        if "exif" in metadata and "GPS" in metadata["exif"]:
            gps = metadata["exif"]["GPS"]
            if "latitude" in gps:
                gps_lat = gps["latitude"]
            if "longitude" in gps:
                gps_lon = gps["longitude"]
                
        # Extract camera info
        camera_make = None
        camera_model = None
        capture_date = None
        date_source = metadata.get("date_source", "exif")
        if "exif" in metadata:
            exif = metadata["exif"]
            camera_make = exif.get("Make")
            camera_model = exif.get("Model")
            capture_date = exif.get("DateTimeOriginal", exif.get("DateTime"))
            
            # Log if date was extracted from filename
            if capture_date and date_source == "filename":
                logger.info(f"Using date from filename for {filename}: {capture_date}")
            
        # Extract VLM description
        description = None
        description_model = None
        if "vlm_description" in metadata:
            vlm = metadata["vlm_description"]
            description = vlm.get("description")
            description_model = vlm.get("model")
            
        # Store full metadata as JSON blob
        metadata_blob = json.dumps(metadata, default=str)
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # Check if file already exists in the database
            cursor.execute("SELECT id FROM images WHERE file_path = ?", (file_path,))
            existing_id = cursor.fetchone()
            
            if existing_id:
                # Get thumbnail path if available
                thumbnail = metadata.get("thumbnail")
                
                # Update existing record
                cursor.execute("""
                    UPDATE images SET
                        filename = ?,
                        format = ?,
                        width = ?,
                        height = ?,
                        exif = ?,
                        gps_lat = ?,
                        gps_lon = ?,
                        capture_date = ?,
                        camera_make = ?,
                        camera_model = ?,
                        description = ?,
                        description_model = ?,
                        thumbnail = ?,
                        last_modified = ?,
                        metadata = ?
                    WHERE id = ?
                """, (
                    filename, img_format, width, height, 
                    json.dumps(metadata.get("exif", {}), default=str),
                    gps_lat, gps_lon, capture_date,
                    camera_make, camera_model,
                    description, description_model,
                    thumbnail, now, metadata_blob, existing_id[0]
                ))
                
                conn.commit()
                return existing_id[0]
            else:
                # Get thumbnail path if available
                thumbnail = metadata.get("thumbnail")
                
                # Insert new record
                cursor.execute("""
                    INSERT INTO images (
                        file_path, filename, format, width, height,
                        exif, gps_lat, gps_lon, capture_date,
                        camera_make, camera_model, description,
                        description_model, thumbnail, added_date, last_modified, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_path, filename, img_format, width, height,
                    json.dumps(metadata.get("exif", {}), default=str),
                    gps_lat, gps_lon, capture_date,
                    camera_make, camera_model, description,
                    description_model, thumbnail, now, now, metadata_blob
                ))
                
                new_id = cursor.lastrowid
                conn.commit()
                return new_id
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding image to database: {str(e)}")
            raise
        finally:
            conn.close()
    
    def batch_add_images(self, metadata_dict: Dict[str, Dict[str, Any]], 
                      progress_callback=None) -> Dict[str, int]:
        """
        Add multiple images to the database.
        
        Args:
            metadata_dict: Dictionary with file paths as keys and metadata as values
            progress_callback: Optional callback function to report progress
            
        Returns:
            Dictionary mapping file paths to database IDs
        """
        results = {}
        total = len(metadata_dict)
        
        for i, (file_path, metadata) in enumerate(metadata_dict.items()):
            # Add file path to metadata if not already present
            if "file_path" not in metadata:
                metadata["file_path"] = file_path
                
            try:
                image_id = self.add_image(metadata)
                results[file_path] = image_id
            except Exception as e:
                logger.error(f"Error adding {file_path}: {str(e)}")
                results[file_path] = None
                
            # Call progress callback if provided
            if progress_callback and callable(progress_callback):
                progress_callback(i+1, total)
                
        return results
    
    def search(self, query: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search for images using full-text search.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of matching image metadata
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Full-text search
            cursor.execute("""
                SELECT i.* FROM images i
                JOIN image_search s ON i.id = s.rowid
                WHERE image_search MATCH ?
                ORDER BY rank
                LIMIT ? OFFSET ?
            """, (query, limit, offset))
            
            results = []
            for row in cursor.fetchall():
                image_data = dict(row)
                
                # Parse JSON fields
                try:
                    if image_data["metadata"]:
                        metadata_obj = json.loads(image_data["metadata"])
                        image_data["metadata"] = metadata_obj
                        
                        # Extract VLM description from metadata if available
                        if "vlm_description" in metadata_obj:
                            image_data["vlm_description"] = metadata_obj["vlm_description"]
                            
                    if image_data["exif"]:
                        image_data["exif"] = json.loads(image_data["exif"])
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse JSON for image ID {image_data['id']}")
                
                results.append(image_data)
                
            return results
            
        finally:
            conn.close()
    
    def filter_search(self, 
                   text_query: Optional[str] = None,
                   camera_make: Optional[str] = None,
                   camera_model: Optional[str] = None,
                   date_start: Optional[str] = None,
                   date_end: Optional[str] = None,
                   min_width: Optional[int] = None,
                   min_height: Optional[int] = None,
                   limit: int = 100, 
                   offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search for images with filters.
        
        Args:
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
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query_parts = []
            params = []
            
            # Build the query conditions
            if text_query:
                query_parts.append("i.id IN (SELECT rowid FROM image_search WHERE image_search MATCH ?)")
                params.append(text_query)
                
            if camera_make:
                query_parts.append("i.camera_make LIKE ?")
                params.append(f"%{camera_make}%")
                
            if camera_model:
                query_parts.append("i.camera_model LIKE ?")
                params.append(f"%{camera_model}%")
                
            if date_start:
                query_parts.append("i.capture_date >= ?")
                params.append(date_start)
                
            if date_end:
                query_parts.append("i.capture_date <= ?")
                params.append(date_end)
                
            if min_width:
                query_parts.append("i.width >= ?")
                params.append(min_width)
                
            if min_height:
                query_parts.append("i.height >= ?")
                params.append(min_height)
                
            # Build the full query
            query = "SELECT * FROM images i"
            if query_parts:
                query += " WHERE " + " AND ".join(query_parts)
                
            query += " ORDER BY capture_date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                image_data = dict(row)
                
                # Parse JSON fields
                try:
                    if image_data["metadata"]:
                        metadata_obj = json.loads(image_data["metadata"])
                        image_data["metadata"] = metadata_obj
                        
                        # Extract VLM description from metadata if available
                        if "vlm_description" in metadata_obj:
                            image_data["vlm_description"] = metadata_obj["vlm_description"]
                            
                    if image_data["exif"]:
                        image_data["exif"] = json.loads(image_data["exif"])
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse JSON for image ID {image_data['id']}")
                
                results.append(image_data)
                
            return results
                
        finally:
            conn.close()
    
    def get_camera_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics about cameras in the collection.
        
        Returns:
            List of camera models and image counts
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT camera_make, camera_model, COUNT(*) as count
                FROM images 
                WHERE camera_make IS NOT NULL AND camera_model IS NOT NULL
                GROUP BY camera_make, camera_model
                ORDER BY count DESC
            """)
            
            result = [{"make": row[0], "model": row[1], "count": row[2]} 
                     for row in cursor.fetchall()]
            return result
            
        finally:
            conn.close()
            
    def get_date_stats(self, by: str = "month") -> List[Dict[str, Any]]:
        """
        Get statistics about image dates.
        
        Args:
            by: Grouping interval ('year', 'month', or 'day')
            
        Returns:
            List of dates and image counts
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            if by == "year":
                date_format = "%Y"
            elif by == "month":
                date_format = "%Y-%m"
            else:  # day
                date_format = "%Y-%m-%d"
                
            cursor.execute(f"""
                SELECT 
                    strftime('{date_format}', capture_date) as date_group,
                    COUNT(*) as count
                FROM images 
                WHERE capture_date IS NOT NULL
                GROUP BY date_group
                ORDER BY date_group
            """)
            
            result = [{"date": row[0], "count": row[1]} 
                     for row in cursor.fetchall()]
            return result
            
        finally:
            conn.close()
                
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # Get total image count
            cursor.execute("SELECT COUNT(*) FROM images")
            total_images = cursor.fetchone()[0]
            
            # Get images with GPS data
            cursor.execute("SELECT COUNT(*) FROM images WHERE gps_lat IS NOT NULL AND gps_lon IS NOT NULL")
            gps_images = cursor.fetchone()[0]
            
            # Get images with VLM descriptions
            cursor.execute("SELECT COUNT(*) FROM images WHERE description IS NOT NULL")
            described_images = cursor.fetchone()[0]
            
            # Get most common image formats
            cursor.execute("""
                SELECT format, COUNT(*) as count
                FROM images 
                GROUP BY format
                ORDER BY count DESC
            """)
            formats = [{"format": row[0], "count": row[1]} for row in cursor.fetchall()]
            
            # Get date range
            cursor.execute("SELECT MIN(capture_date), MAX(capture_date) FROM images WHERE capture_date IS NOT NULL")
            date_range = cursor.fetchone()
            
            return {
                "total_images": total_images,
                "with_gps": gps_images,
                "with_description": described_images,
                "formats": formats,
                "date_range": {
                    "min": date_range[0] if date_range else None,
                    "max": date_range[1] if date_range else None
                }
            }
            
        finally:
            conn.close()
            
    def add_embedding(self, image_id: int, embedding_data: Dict[str, Any]) -> int:
        """
        Add or update a text embedding for an image.
        
        Args:
            image_id: ID of the image
            embedding_data: Dictionary containing embedding data, with keys:
                - embedding: numpy array with embedding
                - text: text that was embedded
                - model: name of the model used for embedding
                - embedding_size: dimensionality of the embedding
                
        Returns:
            ID of the inserted embedding
        """
        # Check if image_id exists
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM images WHERE id = ?", (image_id,))
            if not cursor.fetchone():
                raise ValueError(f"Image ID {image_id} not found in database")
                
            # Extract embedding data
            text = embedding_data.get("text", "")
            model_name = embedding_data.get("model", "unknown")
            embedding_size = embedding_data.get("embedding_size", 0)
            embedding_array = embedding_data.get("embedding")
            
            if embedding_array is None:
                raise ValueError("Embedding data must contain an 'embedding' field")
                
            # Convert numpy array to bytes for storage - make sure it's float32
            if hasattr(embedding_array, "tobytes"):
                # Convert to float32 to ensure consistent storage
                embedding_array = embedding_array.astype(np.float32)
                embedding_blob = embedding_array.tobytes()
            else:
                # If it's not already a numpy array, convert it
                embedding_array = np.array(embedding_array, dtype=np.float32)
                embedding_blob = embedding_array.tobytes()
                
            # Update embedding size to match actual array size
            embedding_size = len(embedding_array)
                
            now = datetime.now(timezone.utc).isoformat()
            
            # Check if embedding for this image and model already exists
            cursor.execute("""
                SELECT id FROM text_embeddings 
                WHERE image_id = ? AND model_name = ?
            """, (image_id, model_name))
            existing_id = cursor.fetchone()
            
            if existing_id:
                # Update existing embedding
                cursor.execute("""
                    UPDATE text_embeddings SET
                        text = ?,
                        embedding_size = ?,
                        embedding = ?,
                        added_date = ?
                    WHERE id = ?
                """, (text, embedding_size, embedding_blob, now, existing_id[0]))
                
                conn.commit()
                return existing_id[0]
            else:
                # Insert new embedding
                cursor.execute("""
                    INSERT INTO text_embeddings (
                        image_id, text, model_name, embedding_size, embedding, added_date
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (image_id, text, model_name, embedding_size, embedding_blob, now))
                
                new_id = cursor.lastrowid
                conn.commit()
                return new_id
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding embedding to database: {str(e)}")
            raise
        finally:
            conn.close()
            
    def batch_add_embeddings(self, 
                           embeddings_dict: Dict[int, Dict[str, Any]], 
                           progress_callback=None) -> Dict[int, int]:
        """
        Add multiple embeddings to the database.
        
        Args:
            embeddings_dict: Dictionary with image IDs as keys and embedding data as values
            progress_callback: Optional callback function to report progress
            
        Returns:
            Dictionary mapping image IDs to embedding IDs
        """
        results = {}
        total = len(embeddings_dict)
        
        for i, (image_id, embedding_data) in enumerate(embeddings_dict.items()):
            try:
                embedding_id = self.add_embedding(image_id, embedding_data)
                results[image_id] = embedding_id
            except Exception as e:
                logger.error(f"Error adding embedding for image {image_id}: {str(e)}")
                results[image_id] = None
                
            # Call progress callback if provided
            if progress_callback and callable(progress_callback):
                progress_callback(i+1, total)
                
        return results
    
    def get_embedding(self, image_id: int, model_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get the embedding for an image.
        
        Args:
            image_id: ID of the image
            model_name: Optional name of the embedding model
            
        Returns:
            Dictionary with embedding data or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            query = "SELECT * FROM text_embeddings WHERE image_id = ?"
            params = [image_id]
            
            if model_name:
                query += " AND model_name = ?"
                params.append(model_name)
                
            query += " ORDER BY added_date DESC LIMIT 1"
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            if not row:
                return None
                
            # Convert blob to numpy array
            embedding_blob = row[5]  # embedding column
            embedding_size = row[4]  # embedding_size column
            embedding_array = np.frombuffer(embedding_blob, dtype=np.float32)
            
            # Verify the embedding size matches the expected size
            if len(embedding_array) != embedding_size:
                logger.warning(f"Retrieved embedding size mismatch: got {len(embedding_array)}, expected {embedding_size}")
                # Attempt to reshape or truncate to the correct size
                if len(embedding_array) > embedding_size:
                    logger.warning(f"Truncating embedding from {len(embedding_array)} to {embedding_size}")
                    embedding_array = embedding_array[:embedding_size]
            
            return {
                "id": row[0],
                "image_id": row[1],
                "text": row[2],
                "model": row[3],
                "embedding_size": embedding_size,
                "embedding": embedding_array,
                "added_date": row[6]
            }
            
        except Exception as e:
            logger.error(f"Error retrieving embedding: {str(e)}")
            return None
        finally:
            conn.close()
            
    def semantic_search(self, 
                      query_embedding: np.ndarray, 
                      limit: int = 20, 
                      model_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for images using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results to return
            model_name: Optional model name to filter embeddings
            
        Returns:
            List of matching image data with similarity scores
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all embeddings, load into memory (more efficient for small-to-medium databases)
            if model_name:
                cursor.execute("""
                    SELECT e.*, i.* FROM text_embeddings e
                    JOIN images i ON e.image_id = i.id
                    WHERE e.model_name = ?
                """, (model_name,))
            else:
                cursor.execute("""
                    SELECT e.*, i.* FROM text_embeddings e
                    JOIN images i ON e.image_id = i.id
                """)
                
            rows = cursor.fetchall()
            
            # Convert embeddings and calculate similarity
            import numpy as np
            from numpy.linalg import norm
            
            results = []
            for row in rows:
                # Convert embedding blob to numpy array
                embedding_blob = row["embedding"]
                embedding_size = row["embedding_size"]
                embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                
                # Ensure the embedding has the correct shape for comparison
                if len(embedding) != len(query_embedding):
                    logger.warning(f"Embedding size mismatch in search: {len(embedding)} vs {len(query_embedding)}")
                    if len(embedding) > len(query_embedding):
                        embedding = embedding[:len(query_embedding)]
                    else:
                        # If the stored embedding is smaller, we need to skip it
                        continue
                
                # Calculate norms
                embedding_norm = norm(embedding)
                query_norm = norm(query_embedding)
                norm_product = embedding_norm * query_norm
                
                # Check for zero norms (which shouldn't happen with valid embeddings)
                if norm_product == 0:
                    if embedding_norm == 0:
                        logger.warning(f"Zero norm encountered for stored embedding (image_id: {row['id']})")
                    if query_norm == 0:
                        logger.warning("Zero norm encountered for query embedding")
                    # Avoid division by zero, but mark as very dissimilar
                    similarity = 0.0
                else:
                    # Calculate cosine similarity
                    similarity = np.dot(embedding, query_embedding) / norm_product
                
                # Create image data dictionary
                image_data = dict(row)
                
                # Parse JSON fields
                try:
                    if image_data["metadata"]:
                        metadata_obj = json.loads(image_data["metadata"])
                        image_data["metadata"] = metadata_obj
                        
                        # Extract VLM description from metadata if available
                        if "vlm_description" in metadata_obj:
                            image_data["vlm_description"] = metadata_obj["vlm_description"]
                            
                    if image_data["exif"]:
                        image_data["exif"] = json.loads(image_data["exif"])
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse JSON for image ID {image_data['id']}")
                
                # Add similarity score
                image_data["similarity"] = float(similarity)
                
                results.append(image_data)
                
            # Sort by similarity (highest first) and limit results
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []
        finally:
            conn.close()
            
    def hybrid_search(self, 
                    text_query: str,
                    query_embedding: np.ndarray,
                    limit: int = 20,
                    model_name: Optional[str] = None,
                    text_weight: float = 0.5) -> List[Dict[str, Any]]:
        """
        Perform a hybrid search combining full-text and semantic search.
        
        Args:
            text_query: Text query for full-text search
            query_embedding: Query embedding vector for semantic search
            limit: Maximum number of results to return
            model_name: Optional model name to filter embeddings
            text_weight: Weight for text search results (0.0 to 1.0)
                        with semantic search weight = 1.0 - text_weight
            
        Returns:
            List of matching image data with combined scores
        """
        # Validate weights
        if text_weight < 0.0 or text_weight > 1.0:
            raise ValueError("text_weight must be between 0.0 and 1.0")
            
        embedding_weight = 1.0 - text_weight
        
        # Get results from both search methods
        text_results = self.search(text_query, limit=limit*2)  # Get more results for better merging
        semantic_results = self.semantic_search(query_embedding, limit=limit*2, model_name=model_name)
        
        # Create dictionaries for faster lookup
        text_dict = {item["id"]: item for item in text_results}
        semantic_dict = {item["id"]: item for item in semantic_results}
        
        # Combine results
        combined_dict = {}
        
        # Process text search results
        for image_id, item in text_dict.items():
            item["text_rank"] = text_results.index(item) + 1
            item["combined_score"] = text_weight * (1.0 / item["text_rank"])
            combined_dict[image_id] = item
            
        # Process semantic search results
        for image_id, item in semantic_dict.items():
            similarity = item["similarity"]
            
            if image_id in combined_dict:
                # Item exists in both result sets
                combined_dict[image_id]["similarity"] = similarity
                combined_dict[image_id]["combined_score"] += embedding_weight * similarity
            else:
                # Item only in semantic results
                item["combined_score"] = embedding_weight * similarity
                combined_dict[image_id] = item
                
        # Convert to list and sort by combined score
        results = list(combined_dict.values())
        results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        return results[:limit]
    
    def clear(self) -> None:
        """Delete all data from the database."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM text_embeddings")
            cursor.execute("DELETE FROM images")
            conn.commit()
            logger.info("Database cleared")
        finally:
            conn.close()
#!/usr/bin/env python3
"""
Image Metadata Extractor

This script extracts metadata from various image formats including:
- JPEG/JPG
- PNG
- TIFF
- GIF
- BMP
- WEBP
- HEIC/HEIF

Dependencies:
- Pillow (PIL)
- piexif (for more detailed EXIF data)
- pyheif (for HEIC/HEIF support)
- transformers, torch (for VLM image description generation)

Install with:
pip install Pillow piexif pyheif transformers torch
"""

import os
import sys
import json
import re
from datetime import datetime
from PIL import Image, ExifTags
import piexif
import argparse
from wheresmy.utils.apple_makernote import decode_apple_makernote, create_clean_json
from wheresmy.core.vlm_describers import get_vlm_describer

try:
    import pyheif
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False
    print("Warning: pyheif not installed. HEIC/HEIF images won't be processed.")

def format_exif_date(date_str):
    """Convert EXIF date format to ISO format."""
    if not date_str:
        return None
    try:
        # Standard EXIF date format: YYYY:MM:DD HH:MM:SS
        dt = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        return dt.isoformat()
    except ValueError:
        return date_str

def extract_date_from_filename(filename):
    """
    Extract date from filename using various common patterns.
    
    Args:
        filename: The filename to extract date from
        
    Returns:
        ISO format date string if found, None otherwise
    """
    # Common patterns:
    # 1. YYYY-MM-DD_HH.MM.SS (or with spaces, dashes, underscores)
    patterns = [
        # YYYY-MM-DD HH.MM.SS or YYYY-MM-DD_HH.MM.SS
        r'(\d{4})[_\-]?(\d{2})[_\-]?(\d{2})[_\s](\d{2})[\.:]?(\d{2})[\.:]?(\d{2})',
        # YYYY-MM-DD
        r'(\d{4})[_\-](\d{2})[_\-](\d{2})',
        # YYYYMMDD_HHMMSS
        r'(\d{4})(\d{2})(\d{2})[_\s](\d{2})(\d{2})(\d{2})',
        # IMG_YYYYMMDD_HHMMSS
        r'IMG[_\-](\d{4})(\d{2})(\d{2})[_\-](\d{2})(\d{2})(\d{2})',
        # Filenames like 2018-04-15 12.11.57.jpg
        r'(\d{4})\-(\d{2})\-(\d{2})\s(\d{2})\.(\d{2})\.(\d{2})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            groups = match.groups()
            if len(groups) == 3:  # Just date, no time
                year, month, day = groups
                try:
                    dt = datetime(int(year), int(month), int(day))
                    return dt.isoformat()
                except ValueError:
                    continue
            elif len(groups) == 6:  # Date and time
                year, month, day, hour, minute, second = groups
                try:
                    dt = datetime(int(year), int(month), int(day), 
                                 int(hour), int(minute), int(second))
                    return dt.isoformat()
                except ValueError:
                    continue
    
    return None

def get_gps_info(exif_data):
    """Extract and format GPS information from EXIF data."""
    if not exif_data or 'GPS' not in exif_data:
        return None
    
    gps = {}
    gps_data = exif_data['GPS']
    
    # GPS latitude
    if 2 in gps_data:
        lat_ref = gps_data.get(1, 'N')
        lat = gps_data[2]
        latitude = lat[0][0]/lat[0][1] + lat[1][0]/(lat[1][1]*60) + lat[2][0]/(lat[2][1]*3600)
        if lat_ref == 'S':
            latitude = -latitude
        gps['latitude'] = latitude
    
    # GPS longitude
    if 4 in gps_data:
        lon_ref = gps_data.get(3, 'E')
        lon = gps_data[4]
        longitude = lon[0][0]/lon[0][1] + lon[1][0]/(lon[1][1]*60) + lon[2][0]/(lon[2][1]*3600)
        if lon_ref == 'W':
            longitude = -longitude
        gps['longitude'] = longitude
    
    # GPS altitude
    if 6 in gps_data:
        alt = gps_data[6]
        altitude = alt[0] / alt[1]
        if gps_data.get(5, 0) == 1:  # 0 = above sea level, 1 = below sea level
            altitude = -altitude
        gps['altitude'] = altitude
    
    # GPS timestamp
    if 7 in gps_data:
        gps['timestamp'] = f"{gps_data[7][0][0]}/{gps_data[7][0][1]}h {gps_data[7][1][0]}/{gps_data[7][1][1]}m {gps_data[7][2][0]}/{gps_data[7][2][1]}s"
    
    return gps

def extract_exif_with_pillow(img):
    """Extract EXIF data using PIL/Pillow."""
    exif_data = {}
    if hasattr(img, '_getexif') and img._getexif():
        for tag, value in img._getexif().items():
            if tag in ExifTags.TAGS:
                tag_name = ExifTags.TAGS[tag]
                # Handle dates
                if tag_name in ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']:
                    exif_data[tag_name] = format_exif_date(value)
                else:
                    exif_data[tag_name] = value
    return exif_data

def extract_exif_with_piexif(image_path):
    """Extract more detailed EXIF data using piexif."""
    try:
        exif_dict = piexif.load(image_path)
        processed_exif = {}
        
        # Process 0th IFD (main image metadata)
        if '0th' in exif_dict and exif_dict['0th']:
            for tag, value in exif_dict['0th'].items():
                tag_name = piexif.TAGS['0th'].get(tag, str(tag))
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8').strip('\x00')
                    except UnicodeDecodeError:
                        value = f"Binary data ({len(value)} bytes)"
                processed_exif[tag_name] = value
        
        # Process Exif IFD (additional metadata)
        if 'Exif' in exif_dict and exif_dict['Exif']:
            exif_info = {}
            for tag, value in exif_dict['Exif'].items():
                tag_name = piexif.TAGS['Exif'].get(tag, str(tag))
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8').strip('\x00')
                    except UnicodeDecodeError:
                        value = f"Binary data ({len(value)} bytes)"
                # Handle date fields
                if tag_name in ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']:
                    if isinstance(value, str):
                        value = format_exif_date(value)
                exif_info[tag_name] = value
            processed_exif['ExifInfo'] = exif_info
        
        # Process GPS IFD (GPS metadata)
        gps_info = get_gps_info(exif_dict)
        if gps_info:
            processed_exif['GPS'] = gps_info
        
        return processed_exif
    
    except (piexif.InvalidImageDataError, ValueError) as e:
        return {"error": f"Error extracting EXIF data with piexif: {str(e)}"}

def extract_heif_metadata(image_path):
    """Extract metadata from HEIC/HEIF images."""
    if not HEIF_SUPPORT:
        return {"error": "HEIC/HEIF support not available. Install pyheif."}
    
    try:
        heif_file = pyheif.read(image_path)
        metadata = {}
        
        # Basic properties
        metadata["bit_depth"] = heif_file.bit_depth
        metadata["mode"] = heif_file.mode
        metadata["size"] = (heif_file.size[0], heif_file.size[1])
        
        # Extract EXIF if available
        for metadata_type in heif_file.metadata or []:
            if metadata_type['type'] == 'Exif':
                exif_data = metadata_type['data']
                # Skip EXIF header
                if exif_data.startswith(b'Exif\x00\x00'):
                    exif_data = exif_data[6:]
                
                try:
                    exif_dict = piexif.load(exif_data)
                    exif_info = {}
                    
                    # Process each IFD
                    for ifd in ['0th', 'Exif', '1st']:
                        if ifd in exif_dict and exif_dict[ifd]:
                            for tag, value in exif_dict[ifd].items():
                                tag_name = piexif.TAGS[ifd].get(tag, str(tag))
                                if isinstance(value, bytes):
                                    try:
                                        value = value.decode('utf-8').strip('\x00')
                                    except UnicodeDecodeError:
                                        value = f"Binary data ({len(value)} bytes)"
                                exif_info[tag_name] = value
                    
                    metadata["EXIF"] = exif_info
                    
                    # Process GPS data
                    gps_info = get_gps_info(exif_dict)
                    if gps_info:
                        metadata['GPS'] = gps_info
                        
                    # Process Apple MakerNote if present
                    maker_note_found = False
                    for ifd in ['0th', 'Exif']:
                        if ifd in exif_dict and exif_dict[ifd]:
                            for tag, value in exif_dict[ifd].items():
                                tag_name = piexif.TAGS[ifd].get(tag, str(tag))
                                if tag_name == "MakerNote" and isinstance(value, bytes):
                                    # Convert bytes to string representation for the decoder
                                    try:
                                        makernote_raw = decode_apple_makernote(value)
                                        metadata["apple_makernote"] = create_clean_json(makernote_raw)
                                        maker_note_found = True
                                        break
                                    except Exception as makernote_e:
                                        metadata["apple_makernote_error"] = f"Error processing Apple MakerNote: {str(makernote_e)}"
                        if maker_note_found:
                            break
                
                except Exception as e:
                    metadata["EXIF_error"] = str(e)
            
            elif metadata_type['type'] == 'XMP':
                # Store raw XMP data 
                metadata["XMP"] = "XMP data available (raw binary not displayed)"
        
        return metadata
    
    except Exception as e:
        return {"error": f"Error extracting HEIF metadata: {str(e)}"}

def extract_metadata(image_path, vlm_describer=None, vlm_prompt=None):
    """
    Extract metadata from an image file.
    
    Args:
        image_path: Path to the image file
        vlm_describer: Optional VLM describer object for generating image descriptions
        vlm_prompt: Optional custom prompt for the VLM
        
    Returns:
        Dictionary containing the extracted metadata
    """
    if not os.path.exists(image_path):
        return {"error": f"File not found: {image_path}"}
    
    file_ext = os.path.splitext(image_path)[1].lower()
    
    try:
        # HEIC/HEIF files need special handling
        if file_ext in ['.heic', '.heif']:
            metadata = extract_heif_metadata(image_path)
        else:
            # For other image formats, use PIL/Pillow
            img = Image.open(image_path)
            
            metadata = {
                "filename": os.path.basename(image_path),
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
            }
            
            # Add image-specific properties
            if hasattr(img, 'info'):
                for key, value in img.info.items():
                    if isinstance(value, (str, int, float, bool, list, dict)):
                        metadata[key] = value
                    elif value is None:
                        metadata[key] = None
                    else:
                        metadata[key] = f"Data of type {type(value).__name__}"
            
            # Extract EXIF data for formats that support it
            if file_ext in ['.jpg', '.jpeg', '.tif', '.tiff']:
                try:
                    exif_data = extract_exif_with_piexif(image_path)
                    if exif_data:
                        metadata["exif"] = exif_data
                        if "MakerNote" in exif_data:
                            try:
                                # Get the raw makernote data first
                                makernote_raw = decode_apple_makernote(exif_data["MakerNote"])
                                # Use the clean_json function to get a more readable representation
                                metadata["apple_makernote"] = create_clean_json(makernote_raw)
                            except Exception as makernote_e:
                                metadata["apple_makernote_error"] = f"Error processing Apple MakerNote: {str(makernote_e)}"
                except Exception as e:
                    # Fallback to simpler EXIF extraction
                    try:
                        exif_data = extract_exif_with_pillow(img)
                        if exif_data:
                            metadata["exif"] = exif_data
                            if "MakerNote" in exif_data:
                                try:
                                    makernote_raw = decode_apple_makernote(exif_data["MakerNote"])
                                    metadata["apple_makernote"] = create_clean_json(makernote_raw)
                                except Exception as makernote_e:
                                    metadata["apple_makernote_error"] = f"Error processing Apple MakerNote: {str(makernote_e)}"
                    except Exception as inner_e:
                        metadata["exif_error"] = f"Error extracting EXIF: {str(inner_e)}"
        
        # If VLM describer is provided, generate image description
        if vlm_describer is not None:
            try:
                description_result = vlm_describer(image_path, prompt=vlm_prompt)
                if "error" in description_result:
                    metadata["vlm_description_error"] = description_result["error"]
                else:
                    metadata["vlm_description"] = description_result
            except Exception as vlm_e:
                metadata["vlm_description_error"] = f"Error generating VLM description: {str(vlm_e)}"
        
        # Check for capture date - if not in EXIF, try to extract from filename
        if "exif" in metadata and ("DateTimeOriginal" in metadata["exif"] or "DateTime" in metadata["exif"]):
            # Already has date info from EXIF
            pass
        else:
            # Try to extract date from filename
            filename = os.path.basename(image_path)
            date_from_filename = extract_date_from_filename(filename)
            if date_from_filename:
                if "exif" not in metadata:
                    metadata["exif"] = {}
                metadata["exif"]["DateTimeOriginal"] = date_from_filename
                metadata["date_source"] = "filename"
        
        return metadata
    
    except Exception as e:
        return {"error": f"Error processing image: {str(e)}"}

def process_directory(directory, output_file=None, recursive=False, vlm_describer=None, vlm_prompt=None):
    """
    Process all images in a directory.
    
    Args:
        directory: Path to the directory containing images
        output_file: Optional path to save JSON output
        recursive: Whether to process subdirectories recursively
        vlm_describer: Optional VLM describer object for generating image descriptions
        vlm_prompt: Optional custom prompt for the VLM
        
    Returns:
        Dictionary containing metadata for all processed images
    """
    results = {}
    
    # Define image extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif']
    
    # Walk through directory
    if recursive:
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if os.path.splitext(filename)[1].lower() in image_extensions:
                    files.append(os.path.join(root, filename))
    else:
        files = [os.path.join(directory, f) for f in os.listdir(directory) 
                 if os.path.isfile(os.path.join(directory, f)) and 
                 os.path.splitext(f)[1].lower() in image_extensions]
    
    # Process each file
    for file_path in files:
        print(f"Processing {file_path}...")
        results[file_path] = extract_metadata(
            file_path, 
            vlm_describer=vlm_describer, 
            vlm_prompt=vlm_prompt
        )
    
    # Output results
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, default=str)
    
    return results

def main():
    """Main function to process command line arguments."""
    parser = argparse.ArgumentParser(description="Extract metadata from images")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="Path to the image file")
    group.add_argument("-d", "--directory", help="Path to directory containing images")
    
    parser.add_argument("-o", "--output", help="Output JSON file (optional)")
    parser.add_argument("-r", "--recursive", action="store_true", help="Process directories recursively")
    parser.add_argument("--vlm", choices=["none", "smolvlm"], default="none", 
                        help="Use VLM to generate image descriptions (default: none)")
    parser.add_argument("--vlm-prompt", help="Custom prompt for VLM description generation")
    parser.add_argument("--cache-dir", help="Directory to cache VLM models")
    
    args = parser.parse_args()
    
    # Initialize VLM if needed
    vlm_describer = None
    if args.vlm != "none":
        try:
            print(f"Initializing {args.vlm} vision-language model...")
            vlm_describer = get_vlm_describer(
                model_name=args.vlm,
                cache_dir=args.cache_dir
            )
        except Exception as e:
            print(f"Error initializing VLM: {str(e)}", file=sys.stderr)
            sys.exit(1)
    
    if args.file:
        result = extract_metadata(
            args.file, 
            vlm_describer=vlm_describer, 
            vlm_prompt=args.vlm_prompt
        )
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4, default=str)
        else:
            print(json.dumps(result, indent=4, default=str))
    
    elif args.directory:
        results = process_directory(
            args.directory, 
            args.output, 
            args.recursive, 
            vlm_describer=vlm_describer,
            vlm_prompt=args.vlm_prompt
        )
        if not args.output:
            print(json.dumps(results, indent=4, default=str))

if __name__ == "__main__":
    main()

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
from datetime import datetime
from PIL import Image, ExifTags
import piexif
import argparse
from apple_makernote_decoder import decode_apple_makernote, create_clean_json
from vlm_describers import get_vlm_describer

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

def extract_metadata(image_path):
    """Extract metadata from an image file."""
    if not os.path.exists(image_path):
        return {"error": f"File not found: {image_path}"}
    
    file_ext = os.path.splitext(image_path)[1].lower()
    
    try:
        # HEIC/HEIF files need special handling
        if file_ext in ['.heic', '.heif']:
            return extract_heif_metadata(image_path)
        
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
        
        return metadata
    
    except Exception as e:
        return {"error": f"Error processing image: {str(e)}"}

def process_directory(directory, output_file=None, recursive=False):
    """Process all images in a directory."""
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
        results[file_path] = extract_metadata(file_path)
    
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
    
    args = parser.parse_args()
    
    if args.file:
        result = extract_metadata(args.file)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4, default=str)
        else:
            print(json.dumps(result, indent=4, default=str))
    
    elif args.directory:
        results = process_directory(args.directory, args.output, args.recursive)
        if not args.output:
            print(json.dumps(results, indent=4, default=str))

if __name__ == "__main__":
    main()

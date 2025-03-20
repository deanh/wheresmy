import re
import struct
import binascii
import io
from datetime import datetime, timedelta
import json

def decode_apple_makernote(makernote_str):
    """
    Decode Apple iOS MakerNote data from a string or bytes representation.
    
    Args:
        makernote_str: String or bytes representation of the MakerNote data
    
    Returns:
        dict: Decoded information from the MakerNote
    """
    # Convert bytes to string if needed
    if isinstance(makernote_str, bytes):
        try:
            makernote_str = makernote_str.decode('latin1')
        except:
            makernote_str = str(makernote_str)
    
    # Clean up the string representation to get the raw bytes
    if makernote_str.startswith('"') and makernote_str.endswith('"'):
        makernote_str = makernote_str[1:-1]
    elif makernote_str.startswith("b'") and makernote_str.endswith("'"):
        makernote_str = makernote_str[2:-1]  # Handle Python bytes repr format
    elif makernote_str.startswith('b"') and makernote_str.endswith('"'):
        makernote_str = makernote_str[2:-1]  # Handle Python bytes repr format
    
    # Convert the escaped string to a proper bytes object
    cleaned_str = makernote_str.encode('latin1')
    cleaned_str = cleaned_str.replace(b'\\x', b'%')
    cleaned_bytes = b''
    i = 0
    while i < len(cleaned_str):
        if cleaned_str[i:i+1] == b'%':
            if i + 3 <= len(cleaned_str):
                try:
                    byte_val = int(cleaned_str[i+1:i+3], 16)
                    cleaned_bytes += bytes([byte_val])
                    i += 3
                except ValueError:
                    cleaned_bytes += cleaned_str[i:i+1]
                    i += 1
            else:
                cleaned_bytes += cleaned_str[i:i+1]
                i += 1
        else:
            cleaned_bytes += cleaned_str[i:i+1]
            i += 1
    
    # Initialize the result dictionary
    result = {
        "type": "Apple iOS MakerNote",
        "raw_data_length": len(cleaned_bytes),
        "identified_structures": []
    }
    
    # Extract the Apple iOS header
    header_match = re.search(b'Apple iOS\x00\x00', cleaned_bytes)
    if header_match:
        result["header"] = "Apple iOS"
        result["header_position"] = header_match.start()
        
        # Check for TIFF header (MM or II) that often follows
        tiff_pos = header_match.end()
        if tiff_pos + 2 <= len(cleaned_bytes):
            tiff_header = cleaned_bytes[tiff_pos:tiff_pos+2]
            if tiff_header == b'MM':
                result["tiff_byte_order"] = "big-endian (Motorola)"
                # Parse IFD structure that typically follows MM
                result["tiff_structure"] = parse_tiff_ifd(cleaned_bytes[tiff_pos:], big_endian=True)
            elif tiff_header == b'II':
                result["tiff_byte_order"] = "little-endian (Intel)"
                result["tiff_structure"] = parse_tiff_ifd(cleaned_bytes[tiff_pos:], big_endian=False)
    
    # Look for binary plists
    plist_positions = [m.start() for m in re.finditer(b'bplist00', cleaned_bytes)]
    result["plist_count"] = len(plist_positions)
    
    # Process each plist position
    for idx, pos in enumerate(plist_positions):
        # Try to extract key metadata around the plist
        start_context = max(0, pos-30)
        before_bytes = cleaned_bytes[start_context:pos]
        after_bytes = cleaned_bytes[pos:min(len(cleaned_bytes), pos+100)]
        
        # Extract values that look like keys before bplists
        key_pattern = re.compile(rb'([A-Za-z0-9]+)(?:\x00+|\s+)bplist00', re.DOTALL)
        key_match = key_pattern.search(cleaned_bytes[max(0, pos-30):pos+8])
        plist_key = None
        if key_match:
            try:
                plist_key = key_match.group(1).decode('ascii')
            except:
                plist_key = key_match.group(1).hex()
        
        # Try to analyze any timestamp-related data
        timestamp_data = {}
        # Look for keywords related to time
        time_keywords = [b'time', b'date', b'epoch', b'scale', b'timestamp']
        found_time_keywords = []
        for keyword in time_keywords:
            if keyword in after_bytes.lower():
                found_time_keywords.append(keyword.decode('ascii'))
        
        # Look for potential values that could be timestamps
        # Common Apple timestamp epoch: January 1, 2001, 00:00:00 UTC
        timestamp_candidates = []
        for i in range(pos, min(len(cleaned_bytes), pos+100)):
            if i + 4 <= len(cleaned_bytes):
                try:
                    # Try both big and little endian
                    val_be = struct.unpack('>I', cleaned_bytes[i:i+4])[0]
                    val_le = struct.unpack('<I', cleaned_bytes[i:i+4])[0]
                    
                    # Check if either value could be a reasonable timestamp (between 2001 and 2030)
                    for val in [val_be, val_le]:
                        if 300000000 < val < 800000000:
                            apple_epoch = datetime(2001, 1, 1)
                            date_time = apple_epoch + timedelta(seconds=val)
                            if 2010 < date_time.year < 2030:
                                timestamp_candidates.append({
                                    "position": i,
                                    "timestamp_value": val,
                                    "date_time": date_time.strftime("%Y-%m-%d %H:%M:%S")
                                })
                except:
                    pass
        
        if timestamp_candidates:
            timestamp_data["candidates"] = timestamp_candidates[:3]  # Limit to top 3
        
        if found_time_keywords:
            timestamp_data["keywords"] = found_time_keywords
        
        structure = {
            "type": "Binary plist",
            "position": pos,
            "content_preview": extract_readable_strings(after_bytes[:50]),
        }
        
        if plist_key:
            structure["potential_key"] = plist_key
            
        if timestamp_data:
            structure["timestamp_data"] = timestamp_data
        
        result["identified_structures"].append(structure)
    
    # Extract UUID if present
    uuid_pattern = rb'([0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12})'
    uuid_matches = list(re.finditer(uuid_pattern, cleaned_bytes))
    if uuid_matches:
        result["device_uuid"] = uuid_matches[0].group(1).decode('ascii')
        result["uuid_position"] = uuid_matches[0].start()
        if len(uuid_matches) > 1:
            result["additional_uuids"] = [m.group(1).decode('ascii') for m in uuid_matches[1:]]
    
    # Look for camera and photo metadata values
    # Scan for values that could represent common photo settings
    
    # 1. ISO Values (typically 100, 200, 400, 800, 1600, etc.)
    iso_values = [100, 200, 400, 800, 1600, 3200, 6400]
    iso_matches = []
    
    for iso in iso_values:
        iso_bytes_be = struct.pack('>H', iso)  # big-endian
        iso_bytes_le = struct.pack('<H', iso)  # little-endian
        
        for iso_bytes in [iso_bytes_be, iso_bytes_le]:
            positions = [m.start() for m in re.finditer(re.escape(iso_bytes), cleaned_bytes)]
            for pos in positions:
                # Only include if this looks like it could be a standalone value
                # (not part of a larger number)
                if pos > 0 and cleaned_bytes[pos-1] == 0:
                    iso_matches.append({
                        "value": iso,
                        "position": pos
                    })
    
    if iso_matches:
        result["potential_iso_values"] = iso_matches
    
    # 2. Aperture values (often stored as APEX values or actual f-numbers)
    # Common apertures: f/1.8, f/2.0, f/2.2, f/2.8, f/4.0
    # We'll look for the actual decimal values
    aperture_values = [1.8, 2.0, 2.2, 2.8, 4.0, 5.6, 8.0]
    aperture_matches = []
    
    for aperture in aperture_values:
        # Try to find as both float and rational representations
        float_bytes_be = struct.pack('>f', aperture)
        float_bytes_le = struct.pack('<f', aperture)
        
        for bytes_val in [float_bytes_be, float_bytes_le]:
            positions = [m.start() for m in re.finditer(re.escape(bytes_val), cleaned_bytes)]
            for pos in positions:
                aperture_matches.append({
                    "value": aperture,
                    "position": pos
                })
    
    if aperture_matches:
        result["potential_aperture_values"] = aperture_matches
    
    # 3. Focal length values (common values for iPhone: 4.0mm, 6.0mm, etc.)
    focal_length_values = [4.0, 6.0, 7.5, 9.0, 12.0, 14.0]
    focal_length_matches = []
    
    for focal in focal_length_values:
        float_bytes_be = struct.pack('>f', focal)
        float_bytes_le = struct.pack('<f', focal)
        
        for bytes_val in [float_bytes_be, float_bytes_le]:
            positions = [m.start() for m in re.finditer(re.escape(bytes_val), cleaned_bytes)]
            for pos in positions:
                focal_length_matches.append({
                    "value": focal,
                    "position": pos
                })
    
    if focal_length_matches:
        result["potential_focal_length_values"] = focal_length_matches
    
    # Extract sequences that might represent coordinates
    coord_matches = []
    # Look for pairs of float values that could be lat/long
    for i in range(len(cleaned_bytes) - 8):
        try:
            val1 = struct.unpack('>f', cleaned_bytes[i:i+4])[0]
            val2 = struct.unpack('>f', cleaned_bytes[i+4:i+8])[0]
            
            # Check if values are in reasonable range for coordinates
            if -90 <= val1 <= 90 and -180 <= val2 <= 180:
                coord_matches.append({
                    "position": i,
                    "values": [val1, val2],
                    "interpretation": f"Possible coordinates: {val1}, {val2}"
                })
        except:
            pass
    
    if coord_matches:
        result["potential_coordinates"] = coord_matches[:3]  # Limit to top 3
    
    return result

def parse_tiff_ifd(data, big_endian=True):
    """
    Parse TIFF IFD (Image File Directory) structure often found in Apple's metadata.
    
    Args:
        data (bytes): Raw bytes containing the TIFF data
        big_endian (bool): Whether the data is big-endian (MM) or little-endian (II)
    
    Returns:
        dict: Extracted TIFF structure information
    """
    if len(data) < 8:  # Not enough data for a minimal IFD
        return {"error": "Insufficient data for TIFF IFD"}
    
    endian_mark = '>' if big_endian else '<'
    
    # Check for valid TIFF header (MM or II followed by magic number 42)
    if not ((data[:2] == b'MM' and big_endian) or (data[:2] == b'II' and not big_endian)):
        return {"error": "Invalid TIFF header"}
    
    try:
        # Read magic number (should be 42)
        magic = struct.unpack(f"{endian_mark}H", data[2:4])[0]
        if magic != 42 and magic != 0x002A:
            return {"error": f"Invalid TIFF magic number: {magic}"}
        
        # Get offset to first IFD
        ifd_offset = struct.unpack(f"{endian_mark}I", data[4:8])[0]
        
        # Basic structure info
        result = {
            "header": data[:2].decode('ascii'),
            "magic": magic,
            "ifd_offset": ifd_offset,
            "entries": []
        }
        
        # If the IFD offset is within our data, try to read entries
        if ifd_offset < len(data) - 2:
            # Get number of entries
            num_entries = struct.unpack(f"{endian_mark}H", data[ifd_offset:ifd_offset+2])[0]
            result["num_entries"] = num_entries
            
            # Parse each entry if we have enough data
            entry_size = 12  # Each IFD entry is 12 bytes
            if ifd_offset + 2 + (num_entries * entry_size) <= len(data):
                for i in range(num_entries):
                    entry_offset = ifd_offset + 2 + (i * entry_size)
                    entry_data = data[entry_offset:entry_offset+entry_size]
                    
                    if len(entry_data) == entry_size:
                        tag = struct.unpack(f"{endian_mark}H", entry_data[0:2])[0]
                        type_id = struct.unpack(f"{endian_mark}H", entry_data[2:4])[0]
                        count = struct.unpack(f"{endian_mark}I", entry_data[4:8])[0]
                        value_offset = struct.unpack(f"{endian_mark}I", entry_data[8:12])[0]
                        
                        entry = {
                            "tag": tag,
                            "tag_name": get_exif_tag_name(tag),
                            "type": get_tiff_type_name(type_id),
                            "count": count,
                            "value_offset": value_offset
                        }
                        
                        # For some simple types, we can extract the actual value
                        if type_id == 3:  # SHORT
                            if count == 1:
                                entry["value"] = value_offset & 0xFFFF
                        elif type_id == 4:  # LONG
                            if count == 1:
                                entry["value"] = value_offset
                        
                        result["entries"].append(entry)
        
        return result
    except Exception as e:
        return {"error": f"Exception parsing TIFF structure: {str(e)}"}

def get_tiff_type_name(type_id):
    """Get the name of a TIFF data type from its ID."""
    types = {
        1: "BYTE",
        2: "ASCII",
        3: "SHORT",
        4: "LONG",
        5: "RATIONAL",
        6: "SBYTE",
        7: "UNDEFINED",
        8: "SSHORT",
        9: "SLONG",
        10: "SRATIONAL",
        11: "FLOAT",
        12: "DOUBLE"
    }
    return types.get(type_id, f"Unknown({type_id})")

def get_exif_tag_name(tag_id):
    """Get the name of an EXIF tag from its ID."""
    exif_tags = {
        0x010E: "ImageDescription",
        0x010F: "Make",
        0x0110: "Model",
        0x0112: "Orientation",
        0x011A: "XResolution",
        0x011B: "YResolution",
        0x0128: "ResolutionUnit",
        0x0131: "Software",
        0x0132: "DateTime",
        0x013B: "Artist",
        0x0213: "YCbCrPositioning",
        0x0214: "ReferenceBlackWhite",
        0x8298: "Copyright",
        0x8769: "ExifIFDPointer",
        0x8825: "GPSInfoIFDPointer",
        0x829A: "ExposureTime",
        0x829D: "FNumber",
        0x8822: "ExposureProgram",
        0x8824: "SpectralSensitivity",
        0x8827: "ISOSpeedRatings",
        0x8828: "OECF",
        0x9000: "ExifVersion",
        0x9003: "DateTimeOriginal",
        0x9004: "DateTimeDigitized",
        0x9101: "ComponentsConfiguration",
        0x9102: "CompressedBitsPerPixel",
        0x9201: "ShutterSpeedValue",
        0x9202: "ApertureValue",
        0x9203: "BrightnessValue",
        0x9204: "ExposureBiasValue",
        0x9205: "MaxApertureValue",
        0x9206: "SubjectDistance",
        0x9207: "MeteringMode",
        0x9208: "LightSource",
        0x9209: "Flash",
        0x920A: "FocalLength",
        0x9214: "SubjectArea",
        0x927C: "MakerNote",
        0x9286: "UserComment",
        0x9290: "SubsecTime",
        0x9291: "SubsecTimeOriginal",
        0x9292: "SubsecTimeDigitized",
        0xA000: "FlashpixVersion",
        0xA001: "ColorSpace",
        0xA002: "PixelXDimension",
        0xA003: "PixelYDimension",
        0xA004: "RelatedSoundFile",
        0xA005: "InteroperabilityIFDPointer",
        0xA20B: "FlashEnergy",
        0xA20C: "SpatialFrequencyResponse",
        0xA20E: "FocalPlaneXResolution",
        0xA20F: "FocalPlaneYResolution",
        0xA210: "FocalPlaneResolutionUnit",
        0xA214: "SubjectLocation",
        0xA215: "ExposureIndex",
        0xA217: "SensingMethod",
        0xA300: "FileSource",
        0xA301: "SceneType",
        0xA302: "CFAPattern",
        0xA401: "CustomRendered",
        0xA402: "ExposureMode",
        0xA403: "WhiteBalance",
        0xA404: "DigitalZoomRatio",
        0xA405: "FocalLengthIn35mmFilm",
        0xA406: "SceneCaptureType",
        0xA407: "GainControl",
        0xA408: "Contrast",
        0xA409: "Saturation",
        0xA40A: "Sharpness",
        0xA40B: "DeviceSettingDescription",
        0xA40C: "SubjectDistanceRange",
        0xA420: "ImageUniqueID",
        0xA430: "CameraOwnerName",
        0xA431: "BodySerialNumber",
        0xA432: "LensSpecification",
        0xA433: "LensMake",
        0xA434: "LensModel",
        0xA435: "LensSerialNumber"
    }
    return exif_tags.get(tag_id, f"Unknown({tag_id:04X})")

def extract_readable_strings(data):
    """Extract ASCII strings from binary data."""
    readable = ""
    current_str = ""
    
    for byte in data:
        if 32 <= byte <= 126:  # ASCII printable
            current_str += chr(byte)
        elif current_str:
            if len(current_str) >= 3:  # Only keep strings of reasonable length
                readable += current_str + " "
            current_str = ""
    
    if current_str and len(current_str) >= 3:
        readable += current_str
    
    return readable.strip()

def create_clean_json(data):
    """
    Convert the parsed data into a clean, human-readable JSON structure.
    
    Args:
        data (dict): The raw parsed data
        
    Returns:
        dict: A clean JSON structure with human-readable values
    """
    clean_json = {
        "type": "Apple iOS MakerNote",
        "metadata": {}
    }
    
    # Device information
    if "device_uuid" in data:
        clean_json["device"] = {
            "uuid": data["device_uuid"]
        }
    
    # TIFF structure clean-up
    if "tiff_structure" in data:
        tiff = data["tiff_structure"]
        if "error" not in tiff:
            tiff_info = {"byte_order": data.get("tiff_byte_order", "Unknown")}
            
            # Extract tag values
            if "entries" in tiff:
                exif_tags = {}
                for entry in tiff["entries"]:
                    tag_name = entry["tag_name"]
                    if "value" in entry:
                        exif_tags[tag_name] = entry["value"]
                
                if exif_tags:
                    tiff_info["exif_tags"] = exif_tags
            
            clean_json["metadata"]["tiff"] = tiff_info
    
    # Binary plists
    if "plist_count" in data and data["plist_count"] > 0:
        plists = []
        
        for plist in data["identified_structures"]:
            plist_info = {}
            
            if "potential_key" in plist:
                plist_info["key"] = plist["potential_key"]
            
            if "content_preview" in plist and plist["content_preview"]:
                plist_info["content"] = plist["content_preview"]
            
            if "timestamp_data" in plist:
                timestamp = plist["timestamp_data"]
                
                if "candidates" in timestamp and timestamp["candidates"]:
                    # Get the first timestamp as most likely
                    best_timestamp = timestamp["candidates"][0]
                    plist_info["timestamp"] = best_timestamp["date_time"]
            
            if plist_info:
                plists.append(plist_info)
        
        if plists:
            clean_json["metadata"]["property_lists"] = plists
    
    # Camera settings
    camera_settings = {}
    
    # ISO values
    if "potential_iso_values" in data and data["potential_iso_values"]:
        # Take the first value as the most likely
        camera_settings["iso"] = data["potential_iso_values"][0]["value"]
    
    # Aperture values
    if "potential_aperture_values" in data and data["potential_aperture_values"]:
        camera_settings["aperture"] = f"f/{data['potential_aperture_values'][0]['value']}"
    
    # Focal length values
    if "potential_focal_length_values" in data and data["potential_focal_length_values"]:
        camera_settings["focal_length"] = f"{data['potential_focal_length_values'][0]['value']}mm"
    
    if camera_settings:
        clean_json["metadata"]["camera_settings"] = camera_settings
    
    # Location data
    if "potential_coordinates" in data and data["potential_coordinates"]:
        coord = data["potential_coordinates"][0]
        clean_json["metadata"]["location"] = {
            "coordinates": coord["values"],
            "note": "Potential location coordinates (latitude, longitude)"
        }
    
    return clean_json

# Example usage
if __name__ == "__main__":
    # Example makernote string from your data
    makernote_example = r"b\"Apple iOS\\x00\\x00\\x01MM\\x00\\x12\\x00\\x01\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\t\\x00\\x02\\x00\\x07\\x00\\x00\\x02.\\x00\\x00\\x00\\xec\\x00\\x03\\x00\\x07\\x00\\x00\\x00h\\x00\\x00\\x03\\x1a\\x00\\x04\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01\\x00\\x05\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\xc5\\x00\\x06\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\xc7\\x00\\x07\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01\\x00\\x08\\x00\\n\\x00\\x00\\x00\\x03\\x00\\x00\\x03\\x82\\x00\\x0c\\x00\\n\\x00\\x00\\x00\\x02\\x00\\x00\\x03\\x9a\\x00\\r\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x0e\\x00\\x0e\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x04\\x00\\x10\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01\\x00\\x11\\x00\\x02\\x00\\x00\\x00%\\x00\\x00\\x03\\xaa\\x00\\x14\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01\\x00\\x17\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00 \\x00\\x00\\x19\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x00\\x00\\x1a\\x00\\x02\\x00\\x00\\x00\\x06\\x00\\x00\\x03\\xd0\\x00\\x1f\\x00\\t\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00bplist00O\\x11\\x02\\x00\\x1b\\x01\\x11\\x01\\xe6\\x00\\xec\\x00\\xb8\\x00\\xaa\\x00\\xc2\\x00\\xcb\\x00\\xdb\\x00\\x04\\x01\\xb2\\x00\\xcb\\x00\\xb8\\x00\\xa5\\x00\\xac\\x00\\x98\\x00\\x19\\x01\\x01\\x01\\xf6\\x00\\xc6\\x00\\xcf\\x00\\xc2\\x00\\xb9\\x00\\xd1\\x00\\xea\\x00\\x06\\x01\\xaa\\x00\\xae\\x00\\xb5\\x00\\xab\\x00\\xb2\\x00\\xa3\\x00\\xe9\\x00\\n\\x01\\xe8\\x00\\xd0\\x00\\xd1\\x00\\xc5\\x00\\xbf\\x00\\xbf\\x00\\xea\\x00\\xfe\\x00\\xa4\\x00\\xa8\\x00\\xb9\\x00\\xb8\\x00\\xb5\\x00\\xaf\\x00\\xed\\x00\\xf1\\x00\\xeb\\x00\\xb9\\x00\\xd3\\x00\\xba\\x00\\xd4\\x00\\xe4\\x00\\xd7\\x00\\xfe\\x00\\x9a\\x00\\xa2\\x00\\xbb\\x00\\xbc\\x00\\xc0\\x00\\xc4\\x00\\xea\\x00\\xe2\\x00\\xca\\x00\\xc6\\x00\\xb5\\x00\\x9d\\x00\\xd9\\x00\\xfa\\x00\\xdc\\x00\\xda\\x00\\x8f\\x00\\xa6\\x00\\xb0\\x00\\xc0\\x00\\xc1\\x00\\xd3\\x00\\xe0\\x00\\xd9\\x00\\xc0\\x00\\xc2\\x00\\xc2\\x00\\xce\\x00\\xd9\\x00\\xe0\\x00\\xaa\\x00\\xbb\\x00\\xa5\\x00\\x9a\\x00\\xa6\\x00\\xc3\\x00\\xce\\x00\\xde\\x00\\xcb\\x00\\xe0\\x00\\xb7\\x00\\xd9\\x00\\xd5\\x00\\xc8\\x00\\xb8\\x00\\xb8\\x00\\xa4\\x00\\xbf\\x00\\xaf\\x00\\xa3\\x00\\xb1\\x00\\xa9\\x00\\xc9\\x00\\xe3\\x00\\xb7\\x00\\xca\\x00\\xa5\\x00\\xcf\\x00\\xdd\\x00\\xd3\\x00\\xe1\\x00\\xbc\\x00\\x9d\\x00\\xae\\x00\\xaa\\x00\\xb6\\x00\\xc3\\x00\\xba\\x00\\xc6\\x00\\xe3\\x00\\xab\\x00\\xad\\x00\\x9c\\x00\\xc0\\x00\\xe0\\x00\\xdc\\x00\\xe0\\x00\\xc5\\x00\\xa5\\x00\\xb4\\x00\\xb4\\x00\\xc3\\x00\\xd3\\x00\\xdf\\x00\\xee\\x00\\xf0\\x00\\x8a\\x00\\x90\\x00\\xac\\x00\\xda\\x00\\xd0\\x00\\xef\\x00\\xd2\\x00\\xb7\\x00\\xb8\\x00\\xcb\\x00\\xb2\\x00\\xb9\\x00\\xdd\\x00\\xed\\x00\\xfc\\x00\\xdb\\x00\\x99\\x00\\x8d\\x00\\xa3\\x00\\xde\\x00\\xd6\\x00\\xef\\x00\\xd7\\x00\\x9e\\x00\\xc6\\x00\\xc4\\x00\\xb2\\x00\\xc5\\x00\\xcf\\x00\\xed\\x00\\xfe\\x00\\xfa\\x00\\x96\\x00\\xb5\\x00\\x98\\x00\\xcd\\x00\\xe7\\x00\\xc6\\x00\\xb2\\x00\\xb7\\x00\\xd9\\x00\\xce\\x00\\xc6\\x00\\xce\\x00\\xe6\\x00\\n\\x01\\xf6\\x00\\x06\\x01\\x97\\x00\\xbe\\x00\\xa1\\x00\\xdf\\x00\\xcd\\x00\\xb1\\x00\\x98\\x00\\xbe\\x00\\xd9\\x00\\xd2\\x00\\xca\\x00\\xdf\\x00\\xfd\\x00B\\x01\\x1e\\x01\\xf0\\x00\\x93\\x00\\xb4\\x00\\xb5\\x00\\xe4\\x00\\xc0\\x00\\xa7\\x00\\xbb\\x00\\xc1\\x00\\xd4\\x00\\xba\\x00\\xdc\\x00\\xee\\x00\\t\\x01\\xca\\x01\\x06\\x01\\x10\\x01\\x9c\\x00\\xae\\x00\\xc6\\x00\\xe0\\x00\\xb8\\x00\\xb1\\x00\\xc5\\x00\\xc7\\x00\\xa7\\x00\\xd0\\x00\\xd3\\x00\\xde\\x00\\xa9\\x01X\\x01\\xf6\\x00/\\x01\\x9e\\x00\\xba\\x00\\xc3\\x00\\xda\\x00\\xb2\\x00\\xbc\\x00\\xcd\\x00\\xd3\\x00\\xb7\\x00\\xe3\\x00\\xfc\\x00\\x11\\x01\\xf2\\x01\\xc5\\x00\\xe6\\x00<\\x01\\x00\\x08\\x00\\x00\\x00\\x00\\x00\\x00\\x02\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x02\\x0cbplist00\\xd4\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08UflagsUvalueYtimescaleUepoch\\x10\\x01\\x13\\x00\\x00\\x919\\xb0\\xe8\\x00\\xc6\\x12;\\x9a\\xca\\x00\\x10\\x00\\x08\\x11\\x17\\x1d'-/8=\\x00\\x00\\x00\\x00\\x00\\x00\\x01\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\t\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00?\\xff\\xff\\xf4;\\x00\\x01\\x888\\xff\\xff\\xca-\\x00\\x01\\xca\\x96\\xff\\xffr\\xb3\\x00\\x00\\x8f\\n\\x00\\x00\\x08Q\\x00\\x00\\x00\\x80\\x00\\x00\\x00+\\x00\\x00\\x00\\x082ADD3835-BCFD-4C9A-B471-29819AF606CF\\x00\\x00q825s\\x00\""
    
    # Call the function with the example data
    decoded_info = decode_apple_makernote(makernote_example)
    
    # Convert to a clean, human-readable JSON structure
    clean_json = create_clean_json(decoded_info)
    
    # Print the JSON
    print(json.dumps(clean_json, indent=2))
    
    # Optional: Save to a file
    # with open('apple_makernote_decoded.json', 'w') as f:
    #     json.dump(clean_json, f, indent=2)
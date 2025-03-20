# Image Metadata Format Documentation

This document describes the metadata format produced by the image metadata extractor. The extractor generates JSON data containing detailed information about images, including technical metadata, EXIF data, Apple MakerNote data, and optionally AI-generated descriptions.

## Basic Structure

The top-level structure of the metadata JSON is as follows:

```json
{
  "filename": "image.jpg",
  "format": "JPEG",
  "mode": "RGB",
  "size": [width, height],
  "width": 3024,
  "height": 4032,
  "exif": { ... },
  "apple_makernote": { ... },
  "vlm_description": { ... },
  ... other image-specific properties ...
}
```

## Basic Image Properties

| Field | Type | Description |
|-------|------|-------------|
| `filename` | String | Name of the image file |
| `format` | String | Format of the image (JPEG, PNG, HEIC, etc.) |
| `mode` | String | Color mode (RGB, RGBA, etc.) |
| `size` | Array | Array containing [width, height] of the image in pixels |
| `width` | Number | Width of the image in pixels |
| `height` | Number | Height of the image in pixels |
| `icc_profile` | String/Object | ICC color profile information (if available) |
| `dpi` | Array | Dots per inch resolution (if available) |

## EXIF Data

The `exif` field contains Exchangeable Image File Format data, which includes camera settings, date/time information, and other technical details:

```json
"exif": {
  "Make": "Apple",
  "Model": "iPhone 8",
  "DateTime": "2018-09-22T10:26:16",
  "ExposureTime": "0.008333333333333333",
  "FNumber": "1.8",
  "ISOSpeedRatings": 32,
  ... other EXIF fields ...
}
```

### Common EXIF Fields

| Field | Type | Description |
|-------|------|-------------|
| `Make` | String | Camera manufacturer |
| `Model` | String | Camera model |
| `Software` | String | Software used to process the image |
| `DateTime` | String | Date and time when the image was created (ISO format) |
| `DateTimeOriginal` | String | Original date and time when the image was taken |
| `ExposureTime` | String | Exposure time in seconds |
| `FNumber` | String | F-number (aperture) value |
| `ISOSpeedRatings` | Number | ISO sensitivity |
| `FocalLength` | String | Focal length of the lens in mm |
| `LensModel` | String | Lens model used to take the photo |
| `Flash` | Number | Flash status code |
| `Orientation` | Number | Orientation code (1-8) |
| `ExposureProgram` | Number | Exposure program used |
| `MeteringMode` | Number | Metering mode used |
| `WhiteBalance` | Number | White balance setting (0=auto, 1=manual) |
| `DigitalZoomRatio` | String | Digital zoom ratio used |
| `SceneCaptureType` | Number | Scene capture type |

### GPS Information

If the image contains GPS data, it will be included in the `GPSInfo` subfield of `exif`:

```json
"GPSInfo": {
  "1": "N",                         // Latitude reference (N/S)
  "2": ["53.0", "26.0", "40.32"],  // Latitude (degrees, minutes, seconds)
  "3": "E",                         // Longitude reference (E/W)
  "4": ["13.0", "53.0", "19.49"],  // Longitude (degrees, minutes, seconds)
  "6": "11.234116623150566",       // Altitude in meters
  ... other GPS fields ...
}
```

## Apple MakerNote Data

For Apple devices (iPhone, iPad), additional proprietary metadata is stored in the MakerNote EXIF tag. This data is parsed and provided in the `apple_makernote` field:

```json
"apple_makernote": {
  "type": "Apple iOS MakerNote",
  "device": {
    "uuid": "2ADD3835-BCFD-4C9A-B471-29819AF606CF"
  },
  "metadata": {
    "property_lists": [ ... ],
    "camera_settings": { ... },
    "location": { ... },
    "tiff": { ... }
  }
}
```

### Apple MakerNote Structure

| Field | Type | Description |
|-------|------|-------------|
| `type` | String | Always "Apple iOS MakerNote" |
| `device.uuid` | String | Device unique identifier |
| `metadata.property_lists` | Array | Binary property lists found in the MakerNote |
| `metadata.camera_settings` | Object | Additional camera settings (ISO, aperture, focal length) |
| `metadata.location` | Object | Potential location coordinates (latitude, longitude) |
| `metadata.tiff` | Object | TIFF structure information from the MakerNote |

## VLM Description

If Vision-Language Model (VLM) image description was enabled, the `vlm_description` field will contain an AI-generated description of the image:

```json
"vlm_description": {
  "description": "A detailed description of the image content...",
  "model": "HuggingFaceTB/SmolVLM-Instruct",
  "processing_time": 2.88,
  "prompt": "Create a detailed description of this image to help users find it with text search."
}
```

### VLM Description Structure

| Field | Type | Description |
|-------|------|-------------|
| `description` | String | AI-generated description of the image content |
| `model` | String | Name of the VLM model used to generate the description |
| `processing_time` | Number | Time in seconds it took to generate the description |
| `prompt` | String | The prompt used to generate the description |

## Error Fields

If errors occur during metadata extraction, they will be reported in specific error fields:

| Field | Type | Description |
|-------|------|-------------|
| `error` | String | General error message if the entire extraction failed |
| `exif_error` | String | Error that occurred while extracting EXIF data |
| `apple_makernote_error` | String | Error that occurred while processing Apple MakerNote data |
| `vlm_description_error` | String | Error that occurred while generating the VLM description |
| `EXIF_error` | String | Error that occurred during HEIF/HEIC EXIF extraction |

## Format-Specific Fields

### HEIF/HEIC-Specific Fields

For HEIF/HEIC images, additional fields may be available:

| Field | Type | Description |
|-------|------|-------------|
| `bit_depth` | Number | Color bit depth |
| `EXIF` | Object | EXIF data extracted from the HEIF container |
| `XMP` | String | XMP metadata information |

## File/Directory Processing

When processing a directory, the output will be a dictionary with file paths as keys and metadata objects as values:

```json
{
  "/path/to/image1.jpg": { ... metadata for image1 ... },
  "/path/to/image2.png": { ... metadata for image2 ... }
}
```

## Usage Examples

### Accessing Basic Image Info

```python
metadata = json.loads(metadata_json)
print(f"Image dimensions: {metadata['width']}x{metadata['height']}")
print(f"Image format: {metadata['format']}")
```

### Working with EXIF Data

```python
if "exif" in metadata:
    camera = f"{metadata['exif'].get('Make', 'Unknown')} {metadata['exif'].get('Model', '')}"
    date_taken = metadata['exif'].get('DateTimeOriginal', 'Unknown')
    print(f"Taken with {camera} on {date_taken}")
```

### Getting GPS Coordinates

```python
if "exif" in metadata and "GPSInfo" in metadata["exif"]:
    gps = metadata["exif"]["GPSInfo"]
    lat = float(gps["2"][0]) + float(gps["2"][1])/60 + float(gps["2"][2])/3600
    if gps["1"] == "S": lat = -lat
    
    lon = float(gps["4"][0]) + float(gps["4"][1])/60 + float(gps["4"][2])/3600
    if gps["3"] == "W": lon = -lon
    
    print(f"GPS coordinates: {lat}, {lon}")
```

### Using VLM Descriptions for Search

```python
if "vlm_description" in metadata:
    description = metadata["vlm_description"]["description"]
    print(f"Image content: {description}")
```
#!/usr/bin/env python3
"""
Tests for date extraction functionality.
"""

# import os
import unittest
from datetime import datetime
from wheresmy.core.metadata_extractor import extract_date_from_filename


class TestDateExtraction(unittest.TestCase):
    """Test case for date extraction functions."""

    def test_extract_date_from_filename_standard_format(self):
        """Test extraction of dates from standard format filenames."""
        # Test YYYY-MM-DD HH.MM.SS format
        self.assertEqual(
            extract_date_from_filename("2018-04-15 12.11.57.jpg"),
            datetime(2018, 4, 15, 12, 11, 57).isoformat(),
        )

        # Test YYYY-MM-DD_HH.MM.SS format
        self.assertEqual(
            extract_date_from_filename("2018-04-15_12.11.57.jpg"),
            datetime(2018, 4, 15, 12, 11, 57).isoformat(),
        )

        # Test YYYY-MM-DD format
        self.assertEqual(
            extract_date_from_filename("2018-04-15.jpg"),
            datetime(2018, 4, 15).isoformat(),
        )

    def test_extract_date_from_filename_camera_format(self):
        """Test extraction of dates from camera-generated filenames."""
        # Test IMG_YYYYMMDD_HHMMSS format (common in some cameras)
        self.assertEqual(
            extract_date_from_filename("IMG_20180415_121157.jpg"),
            datetime(2018, 4, 15, 12, 11, 57).isoformat(),
        )

        # Test YYYYMMDD_HHMMSS format
        self.assertEqual(
            extract_date_from_filename("20180415_121157.jpg"),
            datetime(2018, 4, 15, 12, 11, 57).isoformat(),
        )

    def test_extract_date_from_filename_with_path(self):
        """Test extraction of dates from filenames with paths."""
        # Full path should still work
        self.assertEqual(
            extract_date_from_filename("/path/to/2018-04-15 12.11.57.jpg"),
            datetime(2018, 4, 15, 12, 11, 57).isoformat(),
        )

    def test_extract_date_from_filename_sample_files(self):
        """Test extraction of dates from actual sample filenames."""
        # Test with actual sample filenames from our data
        test_files = [
            "2012-05-13 17.20.00.jpg",
            "2013-12-07 18.34.07.jpg",
            "2014-10-11 22.20.06.jpg",
            "2015-10-27 18.38.52.png",
            "2017-04-22 14.41.44.png",
            "2018-04-15 12.11.57.jpg",
            "2018-07-31 19.13.52.jpg",
            "2018-09-22 09.26.16.jpg",
            "2018-11-13 00.06.45.jpg",
            "2020-11-07 18.49.33.jpg",
        ]

        for filename in test_files:
            # Extract expected date from filename format
            parts = filename.split(" ")
            date_part = parts[0]
            time_part = parts[1].split(".")[0:3]

            year, month, day = map(int, date_part.split("-"))
            hour, minute, second = map(int, time_part)

            expected = datetime(year, month, day, hour, minute, second).isoformat()
            self.assertEqual(extract_date_from_filename(filename), expected)

    def test_extract_date_from_filename_invalid(self):
        """Test that invalid filenames return None."""
        invalid_files = ["nodate.jpg", "IMG_1234.jpg", "DSC00001.jpg", "Screenshot.png"]

        for filename in invalid_files:
            self.assertIsNone(extract_date_from_filename(filename))

    def test_extract_date_from_filename_invalid_dates(self):
        """Test that filenames with invalid dates return None."""
        invalid_dates = [
            "2018-13-32 25.61.61.jpg",  # Invalid month, day, hour, minute, second
            "0000-00-00 00.00.00.jpg",  # All zeros
        ]

        for filename in invalid_dates:
            self.assertIsNone(extract_date_from_filename(filename))


if __name__ == "__main__":
    unittest.main()

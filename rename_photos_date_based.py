#!/usr/bin/env python3
"""
Photo and Video Renaming Tool

This script renames photos and videos based on their creation date metadata.
If no date metadata is found, it uses a sequential counter.

Features:
- Extracts creation dates from EXIF metadata
- Handles both images and videos
- Preserves original files (copies rather than moves)
- Detects and handles duplicate files
- Supports recursive directory processing
- Command-line argument support for automation
"""

import argparse
import contextlib
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from shutil import copy2
from typing import Dict, List, Optional, Tuple, Union

import exiftool
import filetype
from natsort import natsorted, natsort_keygen
from PIL import Image
from tqdm import tqdm


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_file_system_dates(filepath: str) -> Dict[str, str]:
    """
    Get modification and creation dates from file system.

    Args:
        filepath: Path to the file

    Returns:
        Dictionary with modification and creation dates
    """
    mod_date = time.strftime(
        "%Y-%m-%d %H:%M:%S %Z", time.localtime(os.path.getmtime(filepath))
    )
    create_date = time.strftime(
        "%Y-%m-%d %H:%M:%S %Z", time.localtime(os.path.getctime(filepath))
    )

    return {"modification": mod_date, "creation": create_date}


def fix_date_format(date: Optional[str]) -> Optional[str]:
    """
    Fix date format by replacing first two colons with hyphens.

    Args:
        date: Date string to fix

    Returns:
        Fixed date string or None if input was None
    """
    if date is not None and date.count(":") > 2:
        date = date.replace(":", "-", 2)
    return date


def add_timeshift_value(metadata: List[Dict], date: str) -> str:
    """
    Add timeshift value to date based on file modify date metadata.

    Args:
        metadata: Exif metadata dictionary
        date: Date string to adjust

    Returns:
        Adjusted date string
    """
    try:
        timeshift_value = metadata[0]["File:FileModifyDate"].split("+")[1].split(":")[0]
        timeshift_value = int(timeshift_value)

        date_obj = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        adjusted_date = date_obj + timedelta(hours=timeshift_value)
        return adjusted_date.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, IndexError):
        # If the date string is in a different format or the timeshift value can't be parsed
        return date


def get_image_creation_date(filepath: str, date: Optional[str] = None) -> Optional[str]:
    """
    Extract creation date from image metadata.

    Args:
        filepath: Path to the image file
        date: Optional date string from previous extraction attempts

    Returns:
        Creation date string or None if not found
    """
    # Try using exiftool first (more comprehensive)
    try:
        with exiftool.ExifToolHelper() as et:
            metadata = et.get_metadata(filepath)

            # Check multiple possible date fields in priority order
            date_fields = [
                "EXIF:CreateDate",
                "EXIF:DateTimeOriginal",
                "EXIF:ModifyDate",
                "XMP:CreateDate",
                "XMP:DateCreated",
            ]

            for field in date_fields:
                if field in metadata[0]:
                    date = metadata[0][field]
                    logger.debug(f"Found date in {field}: {date}")
                    break
    except Exception as e:
        logger.warning(f"Error reading EXIF data with exiftool: {e}")

    # If exiftool didn't find a date, try PIL
    if date is None:
        try:
            with Image.open(filepath) as img:
                if exif_data := img._getexif():
                    # 36867 is DateTimeOriginal, 36868 is DateTimeDigitized, 306 is DateTime
                    for tag in (36867, 36868, 306):
                        if tag in exif_data:
                            date = exif_data[tag]
                            logger.debug(f"Found date in PIL EXIF tag {tag}: {date}")
                            break
        except Exception as e:
            logger.warning(f"Error opening image with PIL: {e}")
            return None

    return fix_date_format(date)


def get_video_creation_date(filepath: str) -> Optional[str]:
    """
    Extract creation date from video metadata.

    Args:
        filepath: Path to the video file

    Returns:
        Creation date string or None if not found
    """
    try:
        with exiftool.ExifToolHelper() as et:
            metadata = et.get_metadata(filepath)

            # Check multiple possible date fields in priority order
            date_fields = [
                "QuickTime:CreationDate",
                "QuickTime:CreateDate",
                "QuickTime:MediaCreateDate",
                "MP4:CreationTime",
                "RIFF:DateTimeOriginal",
            ]

            for field in date_fields:
                if field in metadata[0]:
                    date = metadata[0][field]
                    logger.debug(f"Found video date in {field}: {date}")

                    # Handle timezone info in QuickTime:CreationDate
                    if field == "QuickTime:CreationDate" and "+" in date:
                        date = date.split("+")[0]

                    date = fix_date_format(date)

                    # Apply timeshift if needed
                    if field == "QuickTime:CreateDate" and "+" in metadata[0].get(
                        "File:FileModifyDate", ""
                    ):
                        date = add_timeshift_value(metadata, date)

                    return date
    except Exception as e:
        logger.warning(f"Error extracting video creation date: {e}")

    return None


def log_file_info(
    file_name: str,
    date: Optional[str],
    kind: Optional[object],
    filepath: str,
    verbose: bool,
) -> None:
    """
    Log file information based on verbosity level.

    Args:
        file_name: Name of the file
        date: Date string if available
        kind: File type information
        filepath: Path to the file
        verbose: Whether to log detailed information
    """
    if not verbose:
        return

    if date is None and kind is not None:
        dates = get_file_system_dates(filepath)
        logger.info(f"No date metadata for {file_name}")
        logger.info(
            f"File system dates - Modified: {dates['modification']}, Created: {dates['creation']}"
        )
    elif date is not None:
        logger.info(f"Found date for {file_name}: {date}")


def construct_filename(
    prefix: str,
    date: Optional[Union[str, int]],
    count: int,
    file_extension: str,
    include_original_name: bool = False,
    original_name: str = "",
) -> str:
    """
    Construct a new filename based on prefix, date, and extension.

    Args:
        prefix: Filename prefix
        date: Date string or counter if no date available
        count: Current file counter
        file_extension: File extension including the dot
        include_original_name: Whether to include the original filename
        original_name: Original filename without extension

    Returns:
        Constructed filename
    """
    if date is None:
        date = count
    elif isinstance(date, str):
        date = date.replace(" ", "_").replace(":", "")

    if include_original_name and original_name:
        # Remove invalid characters from original name
        safe_name = "".join(c for c in original_name if c.isalnum() or c in "_-")
        return f"{prefix}_{date}_{safe_name}{file_extension}"
    else:
        return f"{prefix}_{date}{file_extension}"


def compare_possible_duplicate_images(
    dest_filepath: str, filepath: str, filename: str
) -> Tuple[Union[str, bool], str]:
    """
    Compare two images to check if they are duplicates.

    Args:
        dest_filepath: Path to the destination file
        filepath: Path to the source file
        filename: Filename being checked

    Returns:
        Tuple containing destination filepath (or False) and filename (or empty string)
    """
    with contextlib.suppress(Exception):
        with Image.open(dest_filepath) as org_img, Image.open(filepath) as new_img:
            if org_img == new_img:
                return False, ""
    return dest_filepath, filename


def check_if_file_exists(
    filepath: str, dest_path: str, filename: str, kind: object
) -> Tuple[Union[str, bool], str]:
    """
    Check if a file already exists and handle duplicates.

    Args:
        filepath: Path to the source file
        dest_path: Destination directory
        filename: Proposed filename
        kind: File type information

    Returns:
        Tuple containing destination filepath (or False) and filename (or empty string)
    """
    dest_filepath = os.path.join(dest_path, filename)

    if os.path.exists(dest_filepath):
        # For images, check if they are identical
        if kind.mime.startswith("image"):
            dest_filepath, filename = compare_possible_duplicate_images(
                dest_filepath, filepath, filename
            )
            if not dest_filepath or not filename:
                return False, ""

        # Modify filename to avoid overwriting
        name, ext = os.path.splitext(filename)
        try:
            old_name, date_time = name.rsplit("_", 1)
            if len(date_time) > 6:
                last_char = date_time[-1]
                new_char = chr(ord(last_char) + 1)
            else:
                new_char = "a"
            date_time = date_time[:6] + new_char
            filename = f"{old_name}_{date_time}{ext}"
        except ValueError:
            # If there's no underscore after the prefix (e.g., prefix_1.jpg)
            filename = f"{name}a{ext}"

        # Recursively check if the new filename exists
        dest_filepath, filename = check_if_file_exists(
            filepath, dest_path, filename, kind
        )

    return dest_filepath, filename


def save_renamed_file(
    filepath: str, dest_path: str, filename: str, kind: object, dry_run: bool = False
) -> str:
    """
    Save the file with the new name to the destination path.

    Args:
        filepath: Path to the source file
        dest_path: Destination directory
        filename: New filename
        kind: File type information
        dry_run: If True, don't actually copy the file

    Returns:
        Filename or status message
    """
    dest_filepath, filename = check_if_file_exists(filepath, dest_path, filename, kind)

    if not dest_filepath:
        return "File not saved - duplicate detected"

    if dry_run:
        return f"{filename} (dry run - not copied)"

    try:
        copy2(filepath, dest_filepath)
        return filename
    except Exception as e:
        logger.error(f"Error copying file: {e}")
        return f"Error: {str(e)}"


def get_valid_directory(path: str, create_if_missing: bool = False) -> str:
    """
    Validate a directory path and optionally create it if missing.

    Args:
        path: Directory path to validate
        create_if_missing: Whether to create the directory if it doesn't exist

    Returns:
        Valid directory path

    Raises:
        ValueError: If the path is invalid and cannot be created
    """
    path = os.path.expanduser(path)  # Expand ~ to user home directory

    if os.path.exists(path) and os.path.isdir(path):
        return path

    if not create_if_missing:
        raise ValueError(f"Directory does not exist: {path}")
    try:
        os.makedirs(path, exist_ok=True)
        logger.info(f"Created directory: {path}")
        return path
    except Exception as e:
        raise ValueError(f"Could not create directory '{path}': {e}") from e


def process_file(
    filepath: str,
    prefix: str,
    count: int,
    dest_path: str,
    include_original_name: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> Tuple[Optional[str], int]:
    """
    Process a single file - extract date, construct filename, and save.

    Args:
        filepath: Path to the file
        prefix: Filename prefix
        count: Current file counter
        dest_path: Destination directory
        include_original_name: Whether to include original filename in the new name
        dry_run: If True, don't actually copy files
        verbose: Whether to log detailed information

    Returns:
        Tuple containing date and updated counter
    """
    file_extension = os.path.splitext(filepath)[1]
    file_name = os.path.basename(filepath)
    original_name = os.path.splitext(file_name)[0]
    date = None

    if verbose:
        logger.info(f"Processing file {count}: {file_name}")

    # Determine file type
    kind = filetype.guess(filepath)
    if kind is None:
        logger.warning(f"Unknown filetype: {file_name}")
        return None, count

    # Extract creation date based on file type
    if kind.mime.startswith("image"):
        date = get_image_creation_date(filepath)
    elif kind.mime.startswith("video"):
        date = get_video_creation_date(filepath)

    # Log file information
    log_file_info(file_name, date, kind, filepath, verbose)

    # Construct new filename and save file
    filename = construct_filename(
        prefix, date, count, file_extension, include_original_name, original_name
    )
    result = save_renamed_file(filepath, dest_path, filename, kind, dry_run)

    if verbose:
        logger.info(f"Result: {result}")

    return date, count + 1


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Rename photos and videos based on their creation date metadata."
    )
    parser.add_argument("-p", "--prefix", help="Prefix for renamed files")
    parser.add_argument(
        "-s", "--source", help="Source directory containing files to rename"
    )
    parser.add_argument(
        "-d", "--destination", help="Destination directory for renamed files"
    )
    parser.add_argument(
        "-o",
        "--original-name",
        action="store_true",
        help="Include original filename in the renamed file",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually copying files",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    return parser.parse_args()


def interactive_mode() -> Tuple[str, str, str, bool, bool, bool, bool]:
    """
    Get parameters from user in interactive mode.

    Returns:
        Tuple containing prefix, source path, destination path, include_original_name,
        dry_run, verbose, and debug flags
    """
    prefix = input("\nName prefix:\n>  ")

    while True:
        try:
            source_path = input("Source path:\n> ")
            source_path = get_valid_directory(source_path)
            break
        except ValueError as e:
            print(f"Error: {e}")

    while True:
        try:
            dest_path = input("Destination path:\n> ")
            dest_path = get_valid_directory(dest_path, create_if_missing=True)
            break
        except ValueError as e:
            print(f"Error: {e}")

    include_original = (
        input("Include original filename? (y/n, default: n):\n> ")
        .lower()
        .startswith("y")
    )
    dry_run = (
        input("Dry run (no actual file copying)? (y/n, default: n):\n> ")
        .lower()
        .startswith("y")
    )
    verbose = input("Verbose output? (y/n, default: n):\n> ").lower().startswith("y")
    debug = (
        input("Enable debug logging? (y/n, default: n):\n> ").lower().startswith("y")
    )

    return prefix, source_path, dest_path, include_original, dry_run, verbose, debug


def main() -> None:
    """
    Main function to run the script.
    """
    args = parse_arguments()

    # Get parameters either from command line or interactively
    if args.prefix and args.source and args.destination:
        try:
            prefix = args.prefix
            source_path = get_valid_directory(args.source)
            dest_path = get_valid_directory(args.destination, create_if_missing=True)
            include_original = args.original_name
            dry_run = args.dry_run
            verbose = args.verbose
            debug = args.debug
        except ValueError as e:
            logger.error(f"Error: {e}")
            sys.exit(1)
    else:
        prefix, source_path, dest_path, include_original, dry_run, verbose, debug = (
            interactive_mode()
        )

    # Configure logging level based on parameters
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    elif verbose:
        logger.setLevel(logging.INFO)
        logger.info("Verbose logging enabled")
    else:
        logger.setLevel(logging.WARNING)

    if dry_run:
        logger.warning("DRY RUN MODE - No files will be copied")

    count = 1
    date = None
    kind = None
    nkey = natsort_keygen()

    # Count total files for progress bar
    total_files = sum(len(files) for _, _, files in os.walk(source_path))
    logger.info(f"Found {total_files} files to process")

    # Process all files in the directory and subdirectories
    with tqdm(total=total_files, disable=not verbose) as pbar:
        for subdir, dirs, files in os.walk(source_path):
            dirs.sort(key=nkey)
            for file in natsorted(files):
                filepath = os.path.join(subdir, file)

                # Process current file
                date, count = process_file(
                    filepath,
                    prefix,
                    count,
                    dest_path,
                    include_original,
                    dry_run,
                    verbose,
                )
                kind = filetype.guess(filepath)

                pbar.update(1)

    logger.info(f"Processed {count - 1} files")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

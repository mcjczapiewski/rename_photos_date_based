import os
import time
import filetype
import exiftool
from shutil import copy2
from datetime import datetime, timedelta
from PIL import Image
from natsort import natsorted, natsort_keygen


def print_mod_and_create_date(count, filepath):
    mod_date = os.path.getmtime(filepath)
    mod_date = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(mod_date))
    create_date = os.path.getctime(filepath)
    create_date = time.strftime(
        "%Y-%m-%d %H:%M:%S %Z", time.localtime(create_date)
    )
    mod = "MOD:"
    create = "CREATE:"
    print("NO DATE METADATA")
    print(f"{mod:<30}{mod_date}")
    print(f"{create:<30}{create_date}")
    return count


def get_image_creation_date(filepath, date=None):
    with exiftool.ExifToolHelper() as et:
        metadata = et.get_metadata(filepath)
    if "EXIF:CreateDate" in metadata[0]:
        date = metadata[0]["EXIF:CreateDate"]

    if date is None:
        try:
            with Image.open(filepath) as img:
                exif_data = img._getexif()
                if exif_data:
                    if 36867 in exif_data:
                        date = exif_data[36867]  # DateTimeOriginal
        except:
            print("IMAGE COULD NOT BE OPENED")
            return None

    date = fix_date_format(date)
    return date


def get_video_creation_date(filepath):
    date = None
    with exiftool.ExifToolHelper() as et:
        metadata = et.get_metadata(filepath)
    if "QuickTime:CreationDate" in metadata[0]:
        date = metadata[0]["QuickTime:CreationDate"].split("+")[0]
        date = fix_date_format(date)
    elif "QuickTime:CreateDate" in metadata[0]:
        date = metadata[0]["QuickTime:CreateDate"]
        date = fix_date_format(date)
        if "+" in metadata[0]["File:FileModifyDate"]:
            date = add_timeshift_value(metadata, date)
    return date


def add_timeshift_value(metadata, date):
    try:
        timeshift_value = (
            metadata[0]["File:FileModifyDate"].split("+")[1].split(":")[0]
        )
        timeshift_value = int(timeshift_value)

        date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        date = date + timedelta(hours=timeshift_value)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, IndexError):
        # If the date string is in a different format or the timeshift value can't be parsed
        pass
    return date


def fix_date_format(date):
    if date is not None and date.count(":") > 2:
        date = date.replace(":", "-", 2)
    return date


def print_creation_date(count, date, kind, filepath):
    if date is None and kind is not None:
        count = print_mod_and_create_date(count, filepath)
    elif date is not None:
        print(f"{date}")


def construct_filename(prefix, date, count, file_extension):
    if date is None:
        date = count
    elif isinstance(date, str):
        date = date.replace(" ", "_").replace(":", "")
    filename = f"{prefix}_{date}{file_extension}"
    return filename


def save_renamed_file(filepath, dest_path, filename, kind):
    dest_filepath, filename = check_if_file_exists(
        filepath, dest_path, filename, kind
    )
    if dest_filepath:
        copy2(filepath, dest_filepath)
    return filename if filename else "File not saved - duplicate detected"


def compare_possible_duplicate_images(dest_filepath, filepath, filename):
    try:
        with Image.open(dest_filepath) as org_img, Image.open(filepath) as new_img:
            if org_img == new_img:
                return False, ""
    except:
        pass
    return dest_filepath, filename


def check_if_file_exists(filepath, dest_path, filename, kind):
    dest_filepath = os.path.join(dest_path, filename)
    if os.path.exists(dest_filepath):
        if kind.mime.startswith("image"):
            dest_filepath, filename = compare_possible_duplicate_images(
                dest_filepath, filepath, filename
            )
            if not dest_filepath or not filename:
                return False, ""
        name, ext = os.path.splitext(filename)
        try:
            old_name, date_time = name.rsplit("_", 1)
            if len(date_time) > 6:
                last_char = date_time[-1]
                new_char = chr(ord(last_char) + 1)
            else:
                new_char = "a"
            date_time = date_time[:6] + new_char
            filename = old_name + "_" + date_time + ext
        except ValueError:
            # If there's no underscore after the prefix (e.g., prefix_1.jpg)
            filename = name + "a" + ext
        dest_filepath, filename = check_if_file_exists(
            filepath, dest_path, filename, kind
        )
    return dest_filepath, filename


def main():
    # Image.MAX_IMAGE_PIXELS = None

    prefix = input("\nName prefix:\n>  ")
    
    while True:
        path = input("Origin path:\n> ")
        if os.path.exists(path) and os.path.isdir(path):
            break
        print(f"Error: '{path}' is not a valid directory. Please try again.")
    
    while True:
        dest_path = input("Destination path:\n> ")
        if os.path.exists(dest_path) and os.path.isdir(dest_path):
            break
        try:
            os.makedirs(dest_path, exist_ok=True)
            break
        except:
            print(f"Error: Could not create directory '{dest_path}'. Please try again.")
    
    count = 1
    date = None
    kind = None
    nkey = natsort_keygen()

    for subdir, dirs, files in os.walk(path):
        dirs.sort(key=nkey)
        for file in natsorted(files):
            filepath = os.path.join(subdir, file)
            file_extension = os.path.splitext(file)[1]

            # previous file data
            print_creation_date(count, date, kind, filepath)

            print(f"{count:^6}{file:<35} ", end="")
            date = None
            kind = filetype.guess(filepath)

            if kind is None:
                print("---------------UNKNOWN FILETYPE---------------")
                continue

            elif kind.mime.startswith("image"):
                date = get_image_creation_date(filepath, date)

            elif kind.mime.startswith("video"):
                date = get_video_creation_date(filepath)

            filename = construct_filename(prefix, date, count, file_extension)
            filename = save_renamed_file(filepath, dest_path, filename, kind)
            print(filename)

            count += 1

    if 'filepath' in locals():
        print_creation_date(count, date, kind, filepath)
    else:
        print("No files processed.")


if __name__ == "__main__":
    main()
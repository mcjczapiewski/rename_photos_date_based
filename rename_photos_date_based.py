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


def get_image_creation_date(filepath, file, date):
    with exiftool.ExifToolHelper() as et:
        metadata = et.get_metadata(filepath)
    if "EXIF:CreateDate" in metadata[0]:
        date = metadata[0]["EXIF:CreateDate"]

    if date is None:
        try:
            img = Image.open(filepath)
        except:
            print(f"IMAGE COULD NOT BE OPENED: {file}")
            return None

        exif_data = img._getexif()
        img.close()

        if exif_data:
            if 36867 in exif_data:
                date = exif_data[36867]  # DateTimeOriginal

    date = fix_date_format(date)
    return date


def get_video_creation_date(filepath):
    with exiftool.ExifToolHelper() as et:
        metadata = et.get_metadata(filepath)
    if "QuickTime:CreationDate" in metadata[0]:
        date = metadata[0]["QuickTime:CreationDate"].split("+")[0]
        date = fix_date_format(date)
    elif "QuickTime:CreateDate" in metadata[0]:
        date = metadata[0]["QuickTime:CreateDate"]
        date = fix_date_format(date)
        if "+" in metadata[0]["File:FileModifyDate"]:
            timeshift_value = (
                metadata[0]["File:FileModifyDate"].split("+")[1].split(":")[0]
            )
            timeshift_value = int(timeshift_value)

            date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
            date = date + timedelta(hours=timeshift_value)
            date = date.strftime("%Y-%m-%d %H:%M:%S")
    return date


def fix_date_format(date):
    if date is not None and date.count(":") > 2:
        date = date.replace(":", "-", 2)
    return date


def print_creation_date(count, date, kind, filepath):
    if date is None and kind is not None:
        count = print_mod_and_create_date(count, filepath)
    # elif date is not None:
    # print(f"{date}")


def construct_filename(prefix, date, count, file_extension):
    if date is None:
        date = count
    else:
        date = date.replace(" ", "_").replace(":", "")
    filename = f"{prefix}_{date}{file_extension}"
    return filename


def save_renamed_file(filepath, dest_path, filename):
    dest_filepath, filename = check_if_file_exists(dest_path, filename)
    copy2(filepath, dest_filepath)
    return filename


def check_if_file_exists(dest_path, filename):
    dest_filepath = os.path.join(dest_path, filename)
    if os.path.exists(dest_filepath):
        name, ext = os.path.splitext(filename)
        old_name, date_time = name.rsplit("_", 1)
        if len(date_time) > 6:
            last_char = date_time[-1]
            new_char = chr(ord(last_char) + 1)
        else:
            new_char = "a"
        date_time = date_time[:6] + new_char
        filename = old_name + "_" + date_time + ext
        dest_filepath, filename = check_if_file_exists(dest_path, filename)
    return dest_filepath, filename


def main():
    # Image.MAX_IMAGE_PIXELS = None

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
                date = get_image_creation_date(filepath, file, date)
                # print(construct_filename("test", date, count))

            elif kind.mime.startswith("video"):
                date = get_video_creation_date(filepath)

            filename = construct_filename("test", date, count, file_extension)
            filename = save_renamed_file(filepath, dest_path, filename)
            print(filename)

            count += 1

    print_creation_date(count, date, kind, filepath)


if __name__ == "__main__":
    main()

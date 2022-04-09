import os
import time
import filetype
import exiftool
from datetime import datetime, timedelta
from PIL import Image
from natsort import natsorted, natsort_keygen

# Image.MAX_IMAGE_PIXELS = None

path = r""
count = 1
date = None
nkey = natsort_keygen()


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


def get_image_creation_date(filepath):
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
        if exif_data:
            if 36867 in exif_data:
                date = exif_data[36867]  # DateTimeOriginal
                date = date.replace(":", "-", 2)
                print(f"{0:<30}{date}")

        img.close()
    return date


def get_video_creation_date(filepath):
    with exiftool.ExifToolHelper() as et:
        metadata = et.get_metadata(filepath)
    if "QuickTime:CreationDate" in metadata[0]:
        date = (
            metadata[0]["QuickTime:CreationDate"]
            .replace(":", "-", 2)
            .split("+")[0]
        )
    elif "QuickTime:CreateDate" in metadata[0]:
        date = metadata[0]["QuickTime:CreateDate"].replace(":", "-", 2)
        if "+" in metadata[0]["File:FileModifyDate"]:
            timeshift_value = (
                metadata[0]["File:FileModifyDate"].split("+")[1].split(":")[0]
            )
            timeshift_value = int(timeshift_value)

            date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
            date = date + timedelta(hours=timeshift_value)
            date = date.strftime("%Y-%m-%d %H:%M:%S")
    return date


for subdir, dirs, files in os.walk(path):
    dirs.sort(key=nkey)
    for file in natsorted(files):
        filepath = os.path.join(subdir, file)

        # previous file data
        if date is None and count > 1:
            count = print_mod_and_create_date(count, filepath)
        elif count > 1:
            print(f"{date}")
            date = None

        print(f"\t{count}  {file}")
        count += 1
        kind = filetype.guess(filepath)
        date = None

        if kind is None:
            print(f"UNKNOWN FILETYPE: {file}")
            continue

        elif kind.mime.startswith("image"):
            date = get_image_creation_date(filepath)

        elif kind.mime.startswith("video"):
            date = get_video_creation_date(filepath)

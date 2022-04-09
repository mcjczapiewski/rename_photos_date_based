import os
import time
import filetype
import exiftool
from PIL import Image
from natsort import natsorted, natsort_keygen

# Image.MAX_IMAGE_PIXELS = None

path = r""
count = 1
nkey = natsort_keygen()
tags = {
    36867: "DateTimeOriginal",
    36868: "DateTimeDigitized",
    306: "DateTime",
}
# declare dictionary
d = {"one": 1, "two": 2, "three": 3}


def print_mod_and_create_date(count, file, filepath):
    print(f"\t{count}  {file}")
    count += 1
    mod_date = os.path.getmtime(filepath)
    mod_date = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(mod_date))
    create_date = os.path.getctime(filepath)
    create_date = time.strftime(
        "%Y-%m-%d %H:%M:%S %Z", time.localtime(create_date)
    )
    mod = "MOD:"
    create = "CREATE:"
    print(f"{mod:<30}{mod_date}")
    print(f"{create:<30}{create_date}")


for subdir, dirs, files in os.walk(path):
    dirs.sort(key=nkey)
    for file in natsorted(files):
        if count < 10:
            filepath = os.path.join(subdir, file)
            kind = filetype.guess(filepath)

            if kind is None:
                print(f"UNKNOWN FILETYPE: {file}")
                pass

            elif kind.mime.startswith("image"):
                print_mod_and_create_date(count, file, filepath)

                try:
                    img = Image.open(filepath)
                except:
                    print(f"IMAGE COULD NOT BE OPENED: {file}")
                    continue

                exif_data = img._getexif()
                if not exif_data:
                    print(f"NO EXIF DATA: {file}")
                    continue
                print(exif_data)
                for t in tags:
                    tag = f"{tags[t]}:"
                    date = exif_data[t]
                    date = date.replace(":", "-", 2)
                    print(f"{tag:<30}{date}")

                img.close()

            elif kind.mime.startswith("video"):
                print_mod_and_create_date(count, file, filepath)
                with exiftool.ExifToolHelper() as et:
                    metadata = et.get_metadata(filepath)
                timeshift = False
                if "+" in metadata[0]["File:FileModifyDate"]:
                    timeshift = True
                if "QuickTime:CreationDate" in metadata[0]:
                    date = metadata[0]["QuickTime:CreationDate"].replace(
                        ":", "-", 2
                    )
                elif "QuickTime:CreateDate" in metadata[0]:
                    date = metadata[0]["QuickTime:CreateDate"].replace(
                        ":", "-", 2
                    )
                    if timeshift:
                        date = time.localtime(date)

                print(f"{date}")
                # for d in metadata[0]:
                #     if (
                #         d.endswith("Date")
                #         # and not d.startswith("File:")
                #         # and "Modif" not in d
                #     ):
                #         tag = f"{d}:"
                #         date = metadata[0][d]

import os
import time
import filetype
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
    print(f"{mod:<20}{mod_date}")
    print(f"{create:<20}{create_date}")


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
                for t in tags:
                    tag = f"{tags[t]}:"
                    date = exif_data[t]
                    date = date.replace(":", "-", 2)
                    print(f"{tag:<20}{date}")

                img.close()

            elif kind.mime.startswith("video"):
                print_mod_and_create_date(count, file, filepath)

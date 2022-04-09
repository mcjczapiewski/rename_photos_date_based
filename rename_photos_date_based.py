import os
import time
from PIL import Image
from natsort import natsorted, natsort_keygen

# Image.MAX_IMAGE_PIXELS = None

path = r"/Users/mcjczapiewski/NotInTimeM./SERIES/HIMYM/How I Met Your Mother Season 1"
count = 1
nkey = natsort_keygen()
tags = [
    36867,  # DateTimeOriginal
    36868,  # DateTimeDigitized
    306,  # DateTime
]

for subdir, dirs, files in os.walk(path):
    dirs.sort(key=nkey)
    for file in natsorted(files):
        if count < 10:
            filepath = os.path.join(subdir, file)

            try:
                pimg = Image.open(filepath)
            except:
                continue

            print(f"\t{count}  {file}")
            count += 1
            mod_date = os.path.getmtime(filepath)
            # convert mod_date to datetime
            mod_date = time.strftime(
                "%Y-%m-%d %H:%M:%S %Z", time.localtime(mod_date)
            )
            create_date = os.path.getctime(filepath)
            create_date = time.strftime(
                "%Y-%m-%d %H:%M:%S %Z", time.localtime(create_date)
            )
            print(f"MOD:\t{mod_date}")
            print(f"CREATE:\t{create_date}")

            exif_data = pimg._getexif()
            for t in tags:
                print(exif_data[t])

            pimg.close()

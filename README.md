# rename_photos_date_based

To install packages required by this project, type in shell:  
`pip3 install -r requirements.txt`  
after you clone the repo to your drive.

This script renames images and videos from a directory you provide based on their creation timestamps.  
`format: [prefix]_YYYY-MM-DD_HHMMSS`  
This is **extremely useful** if you have photos taken on one trip by few people and want to stack them in one folder and most importantly, view them in the correct order of shots taken.

Some video format's metadata might be tricky, I hope the most common once are secured.  
If a file does not have EXIF or metadata, it is renamed to reflect the prefix you set and the order number in which it was in the origin folder.  
That way, you can eyeball the spot it should be on the list and rename it by hand.  
You will be asked to provide prefix, path to directory with images to rename and path for renamed images.  
Both paths can be the same, the important part of this is, that files are copied (with all metadata preserved), not moved or deleted.  
I do not want to risk any of your files be destroyed. Remove the old files once you make sure all has been copied and renamed.

Example (prefix: Croatia):

BEFORE | AFTER
--- | ---
P6114455.JPG | Croatia_2022-04-04_112022.JPG
P6114456.JPG | Croatia_2022-04-04_112022a.JPG
P6124545.JPG | Croatia_138.JPG

The second example is a file with exact timestamp (rare case, but occurs). If that happens, files are first compared on image content.
If it is 100% identical (even small light change in images, and it is not identical to the program), the second photo is not saved.
Any subsequent case will have next alphabetical letters.  
The third is of a file without EXIF data.  


### *THE WORK IS NOT OVER YET AND I WILL CONTINUE TO IMPROVE THIS PROJECT OF MY.*  
*I am planning to refactor this of course and I will try to add some UI to it.  
For now, you can try it out by running the script.*

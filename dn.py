import os
import glob
import sys

def getfiles(folder):
    files = []
    extension = "*.pdf"
    filepath = folder + "/**/" + extension
    for file in glob.iglob(filepath, recursive=True):
        files.append(os.path.basename(file))
    return files

folder = "your_path_folder/formats/"
print(getfiles(folder))

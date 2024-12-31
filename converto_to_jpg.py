import os
from pathlib import Path

def add_jpg_extension(folder_path):
    folder = Path(folder_path)
    
    if not folder.exists() or not folder.is_dir():
        print(f"The folder {folder_path} does not exist or is not a directory.")
        return
    
    for file_path in folder.iterdir():
        if file_path.is_file() and file_path.suffix == '':
            new_file_path = file_path.with_suffix('.jpg')
            file_path.rename(new_file_path)
            print(f"Renamed: {file_path.name} to {new_file_path.name}")

if __name__ == "__main__":
    folder_path = "C:/Users/tervi/Spotlight"
    add_jpg_extension(folder_path)
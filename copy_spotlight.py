import os
import shutil
from pathlib import Path
from PIL import Image
import hashlib

def calculate_hash(file_path):
    """Calculate the SHA-256 hash of the file."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def copy_spotlight_images():
    username = os.getlogin()
    source_dir = Path(os.environ['LOCALAPPDATA']) / 'Packages' / 'Microsoft.Windows.ContentDeliveryManager_cw5n1h2txyewy' / 'LocalState' / 'Assets'
    dest_dir = Path(f"C:/Users/{username}/Dropbox/Eltomalturta/myndasyning/Spotlight")
    
    # Create destination directory if it doesn't exist
    dest_dir.mkdir(exist_ok=True)
    print(f"Destination directory: {dest_dir}")
    
    # Get existing hashes in the destination directory
    existing_hashes = set()
    for file_path in dest_dir.glob("*.jpg"):
        existing_hashes.add(calculate_hash(file_path))
    
    # Counter for copied files
    copy_count = len(existing_hashes)
    
    # Process each file in the source directory
    for file_path in source_dir.iterdir():
        if file_path.is_file():
            try:
                # Try to open the file as an image
                with Image.open(file_path) as img:
                    width, height = img.size
                    
                    # Check if image meets our criteria (landscape and minimum size)
                    if width > 1000 and height > 500 and width > height:
                        # Calculate the hash of the source file
                        file_hash = calculate_hash(file_path)
                        
                        # Only copy if the file hash is not in the existing hashes
                        if file_hash not in existing_hashes:
                            # Create destination filename with sequential numbering
                            dest_file = dest_dir / f"spotlight_{copy_count + 1}.jpg"
                            shutil.copy2(file_path, dest_file)
                            existing_hashes.add(file_hash)
                            copy_count += 1
                            print(f"Copied: {dest_file.name}")
                            
            except Exception as e:
                # Skip files that aren't valid images
                print(f"Skipping non-image file: {file_path.name}")
                continue
    
    print(f"\nProcess completed. Copied {copy_count - len(existing_hashes)} new images to {dest_dir}")

if __name__ == "__main__":
    copy_spotlight_images()
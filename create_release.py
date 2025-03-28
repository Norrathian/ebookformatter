import os
import shutil
import zipfile
from datetime import datetime

def create_release_package():
    """Create a release package with the executable and necessary files"""
    # Create release directory
    version = "1.0.0"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    release_name = f"EbookFormatterPro_v{version}_{timestamp}"
    release_dir = os.path.join("releases", release_name)
    
    print(f"Creating release package: {release_name}")
    
    # Create directories
    os.makedirs("releases", exist_ok=True)
    os.makedirs(release_dir, exist_ok=True)
    
    # Copy executable and icon
    shutil.copy2("dist/EbookFormatterPro.exe", release_dir)
    shutil.copy2("icon.ico", release_dir)
    
    # Copy documentation
    shutil.copy2("README.md", release_dir)
    shutil.copy2("LICENSE", release_dir)
    
    # Create zip archive
    zip_path = os.path.join("releases", f"{release_name}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, release_dir)
                zipf.write(file_path, arcname)
    
    print(f"\nRelease package created successfully!")
    print(f"Location: {zip_path}")
    print("\nContents of the release package:")
    print("- EbookFormatterPro.exe (Main application)")
    print("- icon.ico (Application icon)")
    print("- README.md (Documentation)")
    print("- LICENSE (MIT License)")

if __name__ == "__main__":
    create_release_package() 
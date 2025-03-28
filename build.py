import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build():
    """Clean up build artifacts"""
    print("Cleaning build directories...")
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    # Clean .pyc files
    for pyc in Path('.').rglob('*.pyc'):
        pyc.unlink()

def install_dependencies():
    """Install required packages"""
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable...")
    subprocess.check_call([
        'pyinstaller',
        '--clean',
        '--windowed',
        '--onefile',
        '--icon=icon.ico',
        '--name=EbookFormatterPro',
        '--add-data=icon.ico;.',
        'ebook_formatter.py'
    ])

def main():
    """Main build process"""
    try:
        # Clean previous builds
        clean_build()
        
        # Install dependencies
        install_dependencies()
        
        # Build executable
        build_executable()
        
        print("\nBuild completed successfully!")
        print("Executable can be found in the 'dist' directory")
        
    except Exception as e:
        print(f"\nError during build process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
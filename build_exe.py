import PyInstaller.__main__
import os
import sys

home_dir = os.path.expanduser("~")
logo_path = os.path.join(home_dir, "Downloads", "logo.png")

if not os.path.exists(logo_path):
    print("Error: logo.png not found in Downloads folder")
    sys.exit(1)

PyInstaller.__main__.run([
    'code.py',
    '--name=HamichlolUploader',
    '--onefile',
    '--windowed',
    '--icon=' + logo_path,
    '--add-data=' + f'{logo_path};.',
    '--noconsole',
    '--clean',
])
#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 -m pip install --user --upgrade pyinstaller
python3 -m PyInstaller build.spec --noconfirm
rm -rf build
echo "Built dist/SmartOrganizer"
echo "For a .app bundle, run: pyinstaller --windowed --name SmartOrganizer --add-data 'frontend.html:.' --add-data 'assets/tailwind-offline.css:assets' main_entry.py"

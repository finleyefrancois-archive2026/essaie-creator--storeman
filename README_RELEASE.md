# Smart File Organizer Release Guide

Smart File Organizer is a local, offline file organization dashboard. It starts a tiny Python standard-library web server, opens your browser, previews planned moves, and only moves files after confirmation.

## Run from source

```bash
python main_entry.py
```

Open `http://localhost:8787` if the browser does not open automatically.

## Build a single Windows EXE

Requirements on the build computer:

- Python 3.9+
- Internet access only while installing PyInstaller
- 2-3 GB free disk space recommended for the build cache

```bat
build_windows.bat
```

The output is `dist\SmartOrganizer.exe`. Copy that file to any Windows computer or USB drive and double-click it. No admin rights are required.

## Build on macOS or Linux

```bash
./build_mac.sh
```

PyInstaller can only produce native binaries for the operating system it runs on. Build Windows releases on Windows and macOS releases on macOS.

## Data and portability

By default, logs and undo data are written next to the executable so the app remains portable on USB drives. Start with `--appdata` if you prefer the operating system app-data folder.

## Offline assets

The release embeds `frontend.html` and `assets/tailwind-offline.css`. Do not replace these with CDN-only assets before building, or the app will require internet access.

## Safety features

- Preview-first workflow
- Large confirmation modal before moving files
- Undo log for the most recent run
- Locked, missing, or permission-denied files are skipped and reported
- Conflict handling can skip duplicates or keep both with an automatic suffix
- Smart grouping suggests related files using name similarity and timestamp proximity

## Size target

The spec excludes GUI and documentation modules that are not needed by the app. Final size depends on operating system and Python distribution, but should remain comfortably below the target on most Python 3.9+ installs.

# 📁 Smart File Organizer

**A simple, safe file organizer for everyone.** No installation required. Just double-click and organize.

Perfect for grandparents, parents, or anyone who wants to clean up their computer without technical complexity.

## ✨ Features

- **Preview First**: See exactly what will happen before any files move
- **Safe & Reversible**: Undo button restores files if you change your mind
- **Duplicate Detection**: Finds identical files using SHA-256 hashing
- **Smart Organization**: Groups files by type (Documents, Photos, Videos, etc.)
- **Works Offline**: No internet needed after you get the app
- **Portable**: Runs from USB drive, no installation required
- **Large, Clear Interface**: Easy to read buttons and text

## 🚀 Quick Start (No Installation)

### Option 1: Download Ready-to-Use Version
1. Download `SmartOrganizer.exe` (Windows) or `SmartOrganizer` (Mac/Linux)
2. Double-click to run
3. Your browser opens automatically
4. Select a folder to organize
5. Click "Scan Now" to preview
6. Review the changes
7. Click "Start Organizing" when ready

### Option 2: Run from Source (for developers)
```bash
python main_entry.py
```
Then open http://localhost:8787 in your browser.

## 📋 How to Use

1. **Pick Folder**: Choose the messy folder you want to organize
2. **Choose Destination**: Pick where organized files should go (or leave blank for automatic)
3. **Scan Now**: See a preview of all changes - nothing moves yet!
4. **Review**: Check the "Before vs. After" list
5. **Start Organizing**: Click the green button when you're ready
6. **Undo if Needed**: Made a mistake? Click "Undo" to restore everything

## 🛡️ Safety Features

- **Never surprises you**: Preview shows every single file move
- **Confirmation required**: Big warning dialog before moving anything
- **Automatic renaming**: If files have same name, adds `_1`, `_2`, etc.
- **Skip duplicates**: Identical files are detected and skipped
- **Error handling**: Locked or protected files are skipped with clear messages
- **Undo available**: Last action can always be undone

## 📦 Build Your Own Executable

### Windows
```bat
build_windows.bat
```
Output: `dist\SmartOrganizer.exe`

### macOS / Linux
```bash
pip install pyinstaller
pyinstaller build.spec
```

### Requirements for Building
- Python 3.9 or newer
- PyInstaller (installed automatically by build script)
- 2-3 GB free disk space

## 🔒 Security & Privacy

- **Runs locally**: All processing happens on your computer
- **No data collection**: Nothing is sent to the internet
- **Limited access**: Only accesses folders you explicitly choose
- **Path protection**: Prevents accidental access to system files
- **Rate limiting**: Protects against accidental overload

## 📊 What Gets Organized

| Category | File Types |
|----------|------------|
| Documents | PDF, Word, Excel, PowerPoint, Text, CSV |
| Images | JPG, PNG, GIF, BMP, TIFF, WebP, HEIC |
| Videos | MP4, MOV, AVI, MKV, WMV, WebM |
| Audio | MP3, WAV, AAC, FLAC, M4A, OGG |
| Archives | ZIP, RAR, 7Z, TAR, GZ |
| Other | Everything else stays in place |

## ⌨️ Keyboard Shortcuts

- `Ctrl+Z`: Undo last action
- `Ctrl+Enter`: Execute organization (after scan)
- `Escape`: Close dialogs

## ❓ Troubleshooting

**Q: The app won't start**  
A: Make sure you have Python installed if running from source. For the .exe version, try right-clicking and selecting "Run as administrator".

**Q: Files aren't moving**  
A: Check if files are open in another program. Close them and try again.

**Q: "Permission denied" errors**  
A: Some folders need administrator access. Try organizing to a different location like your Desktop or Documents folder.

**Q: Can I organize system folders?**  
A: No, and you shouldn't! The app blocks access to Windows system folders for your safety.

**Q: Where is the undo log stored?**  
A: Next to the executable in a file called `audit_*.json`. On USB drives, it travels with the app.

## 📝 License

MIT License - See LICENSE file for details.

## 🙏 Credits

Built with ❤️ for people who just want their files organized without learning complicated software.

# 📦 Smart File Organizer - Build & Release Guide

For end-user documentation, see [README.md](README.md).

## 🎯 What This Is

Smart File Organizer is a **single-file executable** that runs a local web server and opens in your browser. No installation, no dependencies, no internet required after building.

Perfect for distributing to non-technical users via USB drive or email.

## 🔨 Building

### Windows (Recommended)

1. On a Windows 10/11 computer with Python 3.9+:
   ```bat
   build_windows.bat
   ```

2. Output: `dist\SmartOrganizer.exe` (~15-25 MB)

3. Test on a clean machine:
   - Copy ONLY the .exe to a USB drive
   - Plug into computer with NO Python installed
   - Double-click - it should work!

### macOS / Linux

```bash
pip install pyinstaller
pyinstaller build.spec
```

Note: You need to create a `build.spec` file similar to the Windows version.

## 🧪 Testing Before Release

1. **Clean Machine Test**: Test on a computer with no Python
2. **USB Portability**: Verify it works from USB drive
3. **Undo Function**: Organize files, then click Undo
4. **Error Handling**: Try organizing locked/open files
5. **Large Folders**: Test with 1000+ files
6. **Duplicate Detection**: Include identical files

## 📁 Files Included in Build

The PyInstaller spec should bundle:
- `main_entry.py` - Application entry point
- `web_server.py` - HTTP server
- `organizer_core.py` - File organization logic
- `frontend.html` - User interface
- `assets/tailwind-offline.css` - Styling

## ⚙️ Runtime Options

```bash
# Default: Opens browser, stores data next to EXE
SmartOrganizer.exe

# Custom port
SmartOrganizer.exe --port 9000

# Don't open browser automatically
SmartOrganizer.exe --no-browser

# Store data in OS AppData instead of next to EXE
SmartOrganizer.exe --appdata
```

## 📊 Data Storage

### Portable Mode (Default)
- Undo logs: Next to EXE as `audit_*.json`
- Application data: Same folder as EXE
- Perfect for USB drives

### AppData Mode (--appdata flag)
- Windows: `%APPDATA%\SmartOrganizer\`
- macOS: `~/Library/Application Support/SmartOrganizer/`
- Linux: `~/.local/share/SmartOrganizer/`

## 🔒 Security Features Built-In

✅ Path traversal protection  
✅ Rate limiting (10 requests/minute)  
✅ Input validation on all API endpoints  
✅ Transaction safety with rollback  
✅ Allowed directories whitelist  
✅ Content Security Policy headers  

## 🐛 Troubleshooting Builds

**Build fails with "module not found"**  
→ Ensure all Python files are in the same directory as build.spec

**EXE too large (>50 MB)**  
→ Check that PyInstaller isn't bundling unnecessary modules

**App won't start on clean machine**  
→ Test with `--no-browser` flag and manually open http://localhost:8787

**CSS not loading**  
→ Verify `assets/tailwind-offline.css` is included in build.spec datas

## 📈 Performance Expectations

| Task | Expected Speed |
|------|----------------|
| Scan 100 files | < 1 second |
| Scan 10,000 files | 10-30 seconds |
| Move 1 GB of files | Depends on disk speed |
| Duplicate detection | ~100 MB/sec hashing |

## 🎨 Customization

### Change Categories
Edit `CATEGORY_MAP` in `organizer_core.py`:

```python
CATEGORY_MAP = {
    "Documents": {".pdf", ".doc", ".docx"},
    "MyCustomType": {".xyz", ".abc"},
}
```

### Change Colors/Theme
Edit `assets/tailwind-offline.css` or `frontend.html`

### Add Keyboard Shortcuts
Add to the `<script>` section in `frontend.html`

## 📝 Version History Template

```markdown
## v1.0.0 (YYYY-MM-DD)
- Initial release
- Preview-first design
- SHA-256 duplicate detection
- Undo functionality
- Transaction safety
- Path traversal protection
```

## 🚀 Distribution Tips

1. **VirusTotal**: Upload your .exe before distributing to get a clean report
2. **Code Signing**: Consider signing for Windows SmartScreen (optional)
3. **Instructions**: Include a simple README.txt with the .exe
4. **Test Folder**: Create a test folder with sample files for first-time users
5. **Video Tutorial**: Record a 2-minute screen capture showing how it works

## 📞 Support

For issues or questions, check:
- [README.md](README.md) - User guide
- Tests in `tests/` - Example usage
- Source code comments - Technical details

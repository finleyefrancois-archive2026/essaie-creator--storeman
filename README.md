# Grandma's Storage Helper

A single-file, portable Electron desktop app that helps non-technical people clean up storage safely. It scans folders, detects exact duplicate files, previews every move, organizes files by type and year, and keeps an undo log next to the executable for USB-drive portability.

## Zero-setup release goal

The Windows release is built as `GrandmaStorageHelper.exe`, a portable executable target created by `electron-builder`. It does not install anything, does not require Python, and stores logs in `./data/audit_log.json` beside the executable.

## Run during development

```bash
npm install
npm run dev
```

In a second terminal, compile and launch Electron against the Vite dev server:

```bash
npm run build:dir
npx electron dist/main/main.js
```

## Build the portable Windows EXE

Run this on a Windows 10/11 build computer:

```bash
npm install
npm run build
```

The portable output is written to:

```text
release/GrandmaStorageHelper.exe
```

## Test on a clean machine

1. Copy only `release/GrandmaStorageHelper.exe` to a USB drive.
2. Plug the USB drive into a Windows 10/11 computer with no Node.js, npm, Python, or admin rights.
3. Double-click `GrandmaStorageHelper.exe`.
4. Scan a small test folder first.
5. Confirm the preview shows the exact Before → After plan.
6. Click **Organize Files**.
7. Confirm `data/audit_log.json` appears beside the EXE on the USB drive.
8. Click **Undo Last Action** and verify moved files return to their original folders.

## Safety promises

- Preview-first: files are not moved until the user approves.
- Friendly errors for permission denied, locked files, missing files, and Windows path-too-long problems.
- Duplicate detection uses SHA-256 exact hashes.
- Conflicting destination names are auto-renamed with `_1`, `_2`, and so on.
- Works offline after the app is built.

@echo off
setlocal
cd /d "%~dp0"
python -m pip install --user --upgrade pyinstaller || exit /b 1
python -m PyInstaller build.spec || exit /b 1
if exist build rmdir /s /q build
if exist SmartOrganizer.spec del SmartOrganizer.spec
echo Built dist\SmartOrganizer.exe
endlocal

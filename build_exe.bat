@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
pyinstaller CameraPhotoTools.spec
echo.
echo Done. EXE: dist\CameraPhotoTools.exe
pause

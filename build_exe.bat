@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python assets\generate_icon.py
pyinstaller CameraPhotoTools.spec

if not exist "dist\CameraPhotoTools.exe" (
  echo ERROR: dist\CameraPhotoTools.exe not found.
  goto :done
)

powershell -NoProfile -Command "$p=(Resolve-Path 'dist\CameraPhotoTools.exe').Path; $h=(Get-FileHash -LiteralPath $p -Algorithm MD5).Hash.ToLower(); $n=[IO.Path]::GetFileName($p); [IO.File]::WriteAllText($p+'.md5', $h+' *'+$n+[Environment]::NewLine)"

if exist "dist\CameraPhotoTools.exe.md5" (
  echo MD5: dist\CameraPhotoTools.exe.md5
) else (
  echo ERROR: failed to write dist\CameraPhotoTools.exe.md5
)

:done
echo.
echo Done. EXE: dist\CameraPhotoTools.exe
pause

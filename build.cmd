@echo off

rmdir /s /q .\dist\rd-usb

python pyinstaller/clean.py
python pyinstaller/package-source-code.py

pyinstaller --noconfirm pyinstaller-cli.spec || goto :error

pyinstaller --noconfirm pyinstaller.spec || goto :error
makensis.exe installer.nsi || goto :error

python pyinstaller/rename-binaries.py

goto :EOF

:error
echo Failed with code: %errorlevel%
exit /b %errorlevel%

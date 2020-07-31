@echo off

pyinstaller --noconfirm pyinstaller-cli.spec || goto :error

pyinstaller --noconfirm pyinstaller.spec || goto :error
makensis.exe installer.nsi || goto :error

goto :EOF

:error
echo Failed with code: %errorlevel%
exit /b %errorlevel%

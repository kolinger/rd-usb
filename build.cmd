@echo off
pyinstaller --noconfirm pyinstaller-cli.spec

pyinstaller --noconfirm pyinstaller.spec
makensis.exe installer.nsi

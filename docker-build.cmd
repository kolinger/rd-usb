@echo off
python utils/version.py version.txt || goto :error
set /p VERSION=<version.txt

docker rmi rd-usb
docker build -t rd-usb . || goto :error
docker image save -o ../rd-usb.tar rd-usb || goto :error

goto :end

:error
echo Failed with code: %errorlevel%
exit /b %errorlevel%

:end
del version.txt

@echo off
python utils/version.py version.txt || goto :error
set /p VERSION=<version.txt

docker buildx build --push --builder=builder --platform linux/arm/v7,linux/arm64/v8,linux/amd64 -t kolinger/rd-usb:%VERSION% -t kolinger/rd-usb:latest . || goto :error

goto :end

:error
echo Failed with code: %errorlevel%
exit /b %errorlevel%

:end
del version.txt

import os
import re

version = None
for entry in os.listdir("dist/"):
    match = re.search(r"^rd-usb-source-(v.*)\.zip$", entry)
    if match:
        version = match.group(1)
        break

if version is None:
    raise Exception("rd-usb-source-vX.zip not found")

os.rename("dist/rd-usb.exe", "dist/rd-usb-%s.exe" % version)
os.rename("dist/rd-usb-install.exe", "dist/rd-usb-install-%s.exe" % version)

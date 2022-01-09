import os
from runpy import run_path
import subprocess
import sys

sys.path.append(".")
from utils.version import version

version_script = os.path.realpath("utils/version.py")
run_path(version_script, run_name="write")

exclude = [
    ".git/",
    ".idea/",
    "dist/",
    "build/",
    "venv/",
    "__pycache__/",
    "*.output",
]

for index, pattern in enumerate(exclude):
    exclude[index] = " -x!" + pattern

exclude = " ".join(exclude)

archive = "dist/rd-usb-source-%s.zip" % version

subprocess.check_call("7z a -r %s %s ." % (exclude, archive))

run_path(version_script, run_name="clean")

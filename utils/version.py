import os
import re
import subprocess
import sys

version_txt = os.path.realpath(os.path.join(os.path.dirname(__file__), "../version.txt"))


def detect(fallback="v0", force=False):
    if os.path.exists(version_txt) and not force:
        with open(version_txt, "r") as file:
            return file.read().strip()

    try:
        output = subprocess.check_output("git describe", shell=True)
        output = output.decode("ascii", errors="ignore").strip()

        if not output:
            return fallback

        if not output.startswith("v"):
            output = "v" + output

        return output

    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass

    return fallback


def write(version):
    version = str(version)
    if version != "None":
        version = '"' + version + '"'

    file_path = os.path.realpath(__file__)
    with open(file_path, "r") as file:
        contents = file.read()
        contents = re.sub(r"^(compiled_version = ).*$", r"\1" + version, contents, flags=re.MULTILINE)

    with open(file_path, "w") as file:
        file.write(contents)


compiled_version = None
version = compiled_version if compiled_version else detect()

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else None
else:
    command = __name__

if command == "write":
    write(detect())

elif command == "version.txt":
    with open(version_txt, "w") as file:
        file.write(detect(force=True))

elif command == "clean":
    write(None)

elif command == "detect":
    print(detect())

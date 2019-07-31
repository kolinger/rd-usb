import os
import re
import subprocess


def detect(fallback="v0"):
    try:
        output = subprocess.check_output("git describe")
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

if __name__ == "write":
    write(detect())

if __name__ == "clean":
    write(None)

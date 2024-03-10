import csv
import json
import logging
import os
import sys

# this script will produce on-receive-python-example.log in current directory as log file
# and also on-receive-python-example.csv in current directory as result

# the script is executed by rd-usb thus why logging file is handy to track of what our script is doing on its own
logging.basicConfig(filename="on-receive-python-example.log", encoding="utf-8", level=logging.DEBUG)

try:
    # first argument is path to JSON file contains list of samples
    samples_path = sys.argv[1]
    logging.info("processing %s" % samples_path)

    with open(samples_path, "r") as file:
        samples = json.load(file)

    # here we can do with sample whatever we want - send it to database, some messaging platform, HTTP, ...
    # but for simplicity we just generate CSV
    csv_path = "on-receive-python-example.csv"

    for sample in samples:
        logging.info("found new sample: %s" % json.dumps(sample))

        # create csv if it doesn't exist and populate header
        if not os.path.exists(csv_path):
            with open(csv_path, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(sample.keys())

        # append new sample to csv
        with open(csv_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(sample.values())

    # now we can dispose of temporary file
    os.remove(samples_path)

except KeyboardInterrupt:
    exit(1)
except Exception as e:
    # if anything bad happens we will see it in log
    logging.exception(e)
    exit(1)

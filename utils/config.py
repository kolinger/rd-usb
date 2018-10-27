import json
from json import JSONDecodeError
import os

project_root = os.path.realpath(os.path.dirname(__file__) + "/..")
config_file = project_root + "/config.json"


class Config:
    data = {}

    def __init__(self):
        if os.path.exists(config_file):
            with open(config_file, "r") as file:
                try:
                    self.data = json.load(file)
                except JSONDecodeError:
                    pass

    def read(self, name, fallback=None):
        if name in self.data:
            return self.data[name]
        return fallback

    def write(self, name, value, flush=True):
        self.data[name] = value
        if flush:
            self.flush()

    def flush(self):
        with open(config_file, "w") as file:
            json.dump(self.data, file, indent=True)

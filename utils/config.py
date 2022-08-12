import json
import os
import sys

from appdirs import user_data_dir, user_cache_dir

_data_path = None
_cache_path = None
_args = None

if getattr(sys, "frozen", False):
    static_path = sys._MEIPASS + "/static"
else:
    static_path = os.path.realpath(os.path.dirname(__file__) + "/../static")


def initialize_paths_from_args(args):
    global _data_path
    global _cache_path
    global _args
    _args = args
    if args.data_dir:
        _data_path = args.data_dir
        _cache_path = os.path.join(_data_path, "cache")


def get_args():
    return _args


def get_data_path():
    global _data_path

    if _data_path is None:
        _data_path = user_data_dir("rd-usb", False)

    if not os.path.exists(_data_path):
        os.makedirs(_data_path)

    return _data_path


def get_cache_path():
    global _cache_path

    if _cache_path is None:
        _cache_path = user_cache_dir("rd-usb", False)

    if not os.path.exists(_cache_path):
        os.makedirs(_cache_path)

    return _cache_path


class Config:
    data = {}

    def __init__(self):
        self.config_file = os.path.join(get_data_path(), "config.json")

        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as file:
                try:
                    self.data = json.load(file)
                except ValueError:
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
        with open(self.config_file, "w") as file:
            json.dump(self.data, file, indent=True)

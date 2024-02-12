from contextlib import redirect_stdout
import io
import multiprocessing
import os
import sys
from threading import Thread
from time import sleep
from urllib import request

from screeninfo import screeninfo
import webview

from utils.config import Config, get_data_path, get_cache_path, initialize_paths_from_args
from utils.version import version
from web import run, parse_cli

debug = "FLASK_DEBUG" in os.environ


class Webview:
    title = None
    width = None
    height = None
    x = None
    y = None

    callback = None
    window = None
    loaded = False
    sleep = 0.5

    loading_html = """
        <style>
            html { height: 100%; overflow: hidden; }
            body { height: 100%; font-family: sans-serif; text-align: center; }
            div { display: table; width: 100%; height: 100%; }
            h1 { display: table-cell; vertical-align: middle; margin: 0; }
        </style>
        <body>
            <div>
                <h1>Loading...</h1>
            </div>
        </body>
    """

    def __init__(self, url):
        self.url = url
        self.window_parameters = {
            "text_select": True,
        }

    def start(self):
        Thread(target=self.handle_callback, daemon=True).start()

        parameters = self.window_parameters
        parameters["title"] = self.title
        parameters["width"] = self.width
        parameters["height"] = self.height
        parameters["x"] = self.x
        parameters["y"] = self.y

        self.clamp_coordinates(parameters)

        self.window = webview.create_window(html=self.loading_html, **parameters)
        self.window.events.loaded += self.on_loaded
        self.window.events.closing += self.on_close
        webview.start(debug=debug)

    def on_loaded(self):
        self.window.events.loaded -= self.on_loaded
        self.loaded = True

    def on_close(self):
        config = Config()
        config.write("window_width", self.window.width, False)
        config.write("window_height", self.window.height, False)
        config.write("window_x", self.window.x, flush=False)
        config.write("window_y", self.window.y, flush=False)
        config.flush()

    def handle_callback(self):
        if self.callback:
            Thread(target=self.callback, daemon=True).start()

        while not self.url_ok(self.url) or not self.loaded:
            sleep(self.sleep)

        self.window.load_url(self.url)

    def url_ok(self, url):
        try:
            request.urlopen(url=url)
            return True
        except Exception:
            return False

    def clamp_coordinates(self, parameters):
        # not ideal, this doesn't consider monitors with different resolutions, but it's better than nothing
        extreme = {
            "left": 0,
            "right": 0,
            "top": 0,
            "bottom": 0,
        }

        for monitor in screeninfo.get_monitors():
            if monitor.x < extreme["left"]:
                extreme["left"] = monitor.x

            right = monitor.x + monitor.width
            if right > extreme["right"]:
                extreme["right"] = right

            if monitor.y < extreme["top"]:
                extreme["top"] = monitor.y

            bottom = monitor.y + monitor.height
            if bottom > extreme["bottom"]:
                extreme["bottom"] = bottom

        if parameters["x"] is None or parameters["y"] is None:
            out_of_bounds = True
        else:
            out_of_bounds = False
            if parameters["x"] < extreme["left"]:
                out_of_bounds = True
            elif parameters["x"] + parameters["width"] > extreme["right"]:
                out_of_bounds = True
            elif parameters["y"] < extreme["top"]:
                out_of_bounds = True
            elif parameters["y"] + parameters["height"] > extreme["bottom"]:
                out_of_bounds = True

        if out_of_bounds:
            parameters["x"] = None
            parameters["y"] = None


if __name__ == "__main__":
    def run_view():
        if len(sys.argv) > 1 and "fork" in sys.argv[1]:
            multiprocessing.freeze_support()
            exit(0)

        args = parse_cli(webview=True)
        initialize_paths_from_args(args)

        try:
            from webview.platforms.cef import settings, command_line_switches

            if args.disable_gpu:
                command_line_switches["disable-gpu"] = ""

            settings.update({
                "log_file": os.path.join(get_data_path(), "cef.log"),
                "cache_path": get_cache_path(),
            })
        except ImportError:
            pass  # cef only

        def callback():
            run(args, embedded=True)

        url = "http://%s:%s" % ("127.0.0.1", args.port)
        view = Webview(url)
        view.callback = callback
        view.title = "RD-USB " + version
        config = Config()
        view.width = config.read("window_width", 1250)
        view.height = config.read("window_height", 800)
        view.x = config.read("window_x", None)
        view.y = config.read("window_y", None)
        view.start()


    if getattr(sys, "frozen", False):
        with io.StringIO() as buffer, redirect_stdout(buffer):
            run_view()
    else:
        run_view()

from contextlib import redirect_stdout
import io
import multiprocessing
import os
import sys
from threading import Thread
from time import sleep
from urllib import request

from appdirs import user_cache_dir
import webview
from webview.platforms.cef import settings

from utils.config import data_path
from web import run

debug = "FLASK_DEBUG" in os.environ

settings.update({
    "log_file": data_path + "/cef.log",
    "cache_path": user_cache_dir("rd-usb", False),
})


class Webview:
    title = None
    width = None
    height = None

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
        self.window_parameters = {}

    def start(self):
        Thread(target=self.handle_callback, daemon=True).start()

        parameters = self.window_parameters
        if self.title:
            parameters["title"] = self.title
        if self.width:
            parameters["width"] = self.width
        if self.height:
            parameters["height"] = self.height

        self.window = webview.create_window(html=self.loading_html, **parameters)
        self.window.loaded += self.on_loaded
        webview.start(debug=debug, gui="cef")

    def on_loaded(self):
        self.window.loaded -= self.on_loaded
        self.loaded = True

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


if __name__ == "__main__":
    def run_view():
        if len(sys.argv) > 1 and "fork" in sys.argv[1]:
            multiprocessing.freeze_support()
            exit(0)

        def callback():
            run(False)

        url = "http://%s:%s" % ("127.0.0.1", 5000)
        view = Webview(url)
        view.callback = callback
        view.title = "RD-USB"
        view.width = 1250
        view.height = 800
        view.start()


    if getattr(sys, "frozen", False):
        with io.StringIO() as buffer, redirect_stdout(buffer):
            run_view()
    else:
        run_view()

import argparse
import logging
from logging import StreamHandler
from logging.handlers import TimedRotatingFileHandler
import multiprocessing
import random
import string
import sys
from threading import Thread
from time import sleep
from urllib import request
import webbrowser

from flask import Flask
import socketio
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from utils.config import Config, static_path, get_data_path, initialize_paths_from_args
from utils.storage import Storage
from webapp.backend import Backend
from webapp.index import Index


def url_ok(url):
    try:
        request.urlopen(url=url)
        return True
    except Exception:
        return False


def parse_cli(open_browser=True, webview=False):
    parser = argparse.ArgumentParser()
    parser.add_argument("port", nargs="?", type=int, default=5000, help="Port for web server to listen on")
    parser.add_argument("--listen", type=str, default="0.0.0.0",
                        help="Listen on address of specific interface (defaults to all interfaces)")
    parser.add_argument("--on-receive", help="Call this program/script when new measurements are received")
    parser.add_argument("--on-receive-interval", type=int, default=60, help="Interval for --on-receive (in seconds)")
    parser.add_argument("--data-dir", type=str, help="Where to store configuration and user data files")
    if webview:
        parser.add_argument("--disable-gpu", action="store_true", default=False, help="Disable GPU rendering")
    else:
        parser.add_argument("--daemon", action="store_true", default=not open_browser, help="Do not launch web browser")
        parser.add_argument("--prefix", default="/", help="If you want to reverse-proxy from path, like /rd-usb")

    return parser.parse_args()


def run(args=None, embedded=False):
    if not args:
        args = parse_cli()

    if not embedded:
        initialize_paths_from_args(args)

    port = args.port
    listen = args.listen
    daemon = "daemon" in args and args.daemon

    if "prefix" in args:
        prefix = args.prefix
    else:
        prefix = "/"
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    if len(prefix) > 1 and prefix.endswith("/"):
        prefix = prefix[0:-1]

    app = Flask(__name__, static_folder=static_path)
    app.config["embedded"] = embedded
    app.config["app_prefix"] = prefix
    app.register_blueprint(Index().register())

    if prefix != "/":
        def fallback(env, resp):
            resp(b"200 OK", [(b"Content-Type", b"text/plain; charset=UTF-8")])
            return [b"use '%s' instead" % prefix.encode("utf-8")]

        app.config["APPLICATION_ROOT"] = prefix
        app.wsgi_app = DispatcherMiddleware(fallback, {prefix: app.wsgi_app})

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    console = StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if not app.debug:
        file = TimedRotatingFileHandler(get_data_path() + "/error.log", when="w0", backupCount=14)
        file.setLevel(logging.ERROR)
        file.setFormatter(formatter)
        logger.addHandler(file)

    try:
        config = Config()
        secret_key = config.read("secret_key")
        if not secret_key:
            secret_key = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(16))
            config.write("secret_key", secret_key)
        app.secret_key = secret_key

        Storage().init()

        sockets = socketio.Server(async_mode="threading", cors_allowed_origins="*")
        socketio_path = "socket.io"
        if len(prefix) > 1:
            socketio_path = prefix[1:] + "/" + socketio_path
        app.wsgi_app = socketio.Middleware(sockets, app.wsgi_app, socketio_path=socketio_path)
        sockets.register_namespace(Backend(args.on_receive, args.on_receive_interval))

        if not embedded:
            def open_in_browser():
                logging.info("Application is starting...")

                url = "http://127.0.0.1:%s" % port
                while not url_ok(url):
                    sleep(0.5)

                logging.info("Application is available at " + url)

                if not app.debug and not daemon:
                    webbrowser.open(url)

            Thread(target=open_in_browser, daemon=True).start()

        app.run(host=listen, port=port, threaded=True, use_reloader=False)

    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        logging.exception(sys.exc_info()[0])


if __name__ == "__main__":
    if len(sys.argv) > 1 and "fork" in sys.argv[1]:
        multiprocessing.freeze_support()
        exit(0)

    if sys.platform.startswith("win"):
        multiprocessing.freeze_support()

    run()

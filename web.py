import logging
from logging import StreamHandler
from logging.handlers import TimedRotatingFileHandler
import secrets
import sys
import threading
import time
from urllib import request
import webbrowser

from engineio import async_threading
from flask import Flask
import socketio

from utils.config import Config, static_path, data_path
from utils.storage import Storage
from webapp.backend import Backend
from webapp.index import Index

this_is_just_for_pyinstaller = async_threading._async

port = 5000
if len(sys.argv) > 1:
    port = int(sys.argv[1])

app = Flask(__name__, static_folder=static_path)
app.register_blueprint(Index().register())

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

console = StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(formatter)
logger.addHandler(console)

if not app.debug:
    file = TimedRotatingFileHandler(data_path + "/error.log", when="w0", backupCount=14)
    file.setLevel(logging.ERROR)
    file.setFormatter(formatter)
    logger.addHandler(file)

try:
    config = Config()
    secret_key = config.read("secret_key")
    if not secret_key:
        secret_key = secrets.token_hex(16)
        config.write("secret_key", secret_key)
    app.secret_key = secret_key

    Storage().init()

    sockets = socketio.Server(async_mode="threading")
    app.wsgi_app = socketio.Middleware(sockets, app.wsgi_app)
    sockets.register_namespace(Backend())

    if __name__ == "__main__":
        if not app.debug:
            def open_in_browser():
                logging.info("Application is starting...")
                url = "http://127.0.0.1:" + str(port)

                while True:
                    try:
                        request.urlopen(url=url)
                        break
                    except Exception:
                        time.sleep(0.5)

                logging.info("Application is available at " + url)
                webbrowser.open(url)


            threading.Timer(1, open_in_browser).start()

        app.run(host="0.0.0.0", port=port, threaded=True)

except (KeyboardInterrupt, SystemExit):
    raise
except:
    logging.exception(sys.exc_info()[0])

import logging
from logging import StreamHandler
import secrets
import sys
import threading
import time
from urllib import request
import webbrowser

from flask import Flask
import socketio

from utils.config import Config
from utils.storage import Storage
from webapp.backend import Backend
from webapp.index import Index

port = 5000
if len(sys.argv) > 1:
    port = int(sys.argv[1])

app = Flask(__name__)
app.register_blueprint(Index().register())

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

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

console = StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(formatter)
logger.addHandler(console)

if __name__ == "__main__":
    if not app.debug:
        def open_in_browser():
            logging.info("Server is starting...")
            url = "http://127.0.0.1:" + str(port)

            while True:
                try:
                    request.urlopen(url=url)
                    break
                except Exception:
                    time.sleep(0.5)

            logging.info("Server is running!")
            webbrowser.open(url)


        threading.Timer(1, open_in_browser).start()

    app.run(host="0.0.0.0", port=port, threaded=True)

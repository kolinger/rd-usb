import json
import logging
import sys
from threading import Thread
import time
import traceback

import arrow
from socketio import Namespace

from utils.config import Config
from utils.formatting import Format
from utils.rdusb import Interface
from utils.storage import Storage


class Backend(Namespace):
    config = None

    def __init__(self):
        super().__init__()
        self.daemon = Daemon(self)

    def init(self):
        self.config = Config()

    def on_open(self, sid, data):
        self.init()

        data = json.loads(data)
        self.config.write("version", data["version"])
        self.config.write("port", data["port"])
        self.config.write("name", data["name"])
        try:
            self.config.write("rate", float(data["rate"]))
        except ValueError:
            pass

        self.emit("connecting")
        self.daemon.start()

    def on_close(self, sid):
        self.init()
        self.emit("disconnecting")
        self.daemon.stop()


class Daemon:
    running = None
    thread = None
    storage = None
    config = None

    def __init__(self, backend):
        self.backed = backend
        self.storage = Storage()
        if self.storage.fetch_status() != "disconnected":
            self.storage.update_status("disconnected")

    def start(self):
        self.running = True
        if self.thread is None:
            self.thread = Thread(target=self.run)
        if not self.thread.is_alive():
            self.thread.start()

    def stop(self):
        self.log("Disconnecting")
        self.running = False
        while self.thread and self.thread.is_alive():
            time.sleep(0.1)
        self.emit("disconnected")

    def run(self):
        self.storage = Storage()
        self.config = Config()
        interface = Interface(port=self.config.read("port"))
        if self.config.read("version") == "UM25C":
            interface.enable_higher_resolution()

        try:
            self.log("Connecting")
            interface.connect()
            self.emit("connected")
            self.log("Connected")

            while self.running:
                data = interface.read()
                self.log(json.dumps(data))
                if data:
                    data["name"] = self.config.read("name")
                    self.update(data)
                self.storage.store_measurement(data)
                time.sleep(self.config.read("rate"))

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            logging.exception(sys.exc_info()[0])
            self.emit("log", traceback.format_exc())
        finally:
            interface.close()
            self.emit("disconnected")
            self.log("Disconnected")
            self.thread = None

    def update(self, data):
        format = Format()

        table = []
        for name in format.table_fields:
            callback = getattr(format, name)
            table.append(callback(data))

        graph = {}
        for name in format.graph_fields:
            if name == "timestamp":
                callback = getattr(format, name)
                value = callback(data)
            else:
                value = data[name]
            graph[name] = value

        self.emit("update", json.dumps({
            "table": table,
            "graph": graph,
        }))

    def emit(self, event, data=None):
        if event == "log":
            self.storage.log(data)
        elif event in ["connecting", "connected", "disconnecting", "disconnected"]:
            self.storage.update_status(event)
        self.backed.emit(event, data)

    def log(self, message):
        prefix = arrow.now().format("YYYY-MM-DD HH:mm:ss") + " - "
        self.emit("log", prefix + message + "\n")

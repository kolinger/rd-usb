import asyncio
import json
import logging
import re
import sys
from threading import Thread
import time
import traceback

import arrow
from socketio import Namespace

from utils.ble import Ble
from utils.config import Config
from utils.formatting import Format
from utils.rdusb import Interface
from utils.storage import Storage


class Backend(Namespace):
    config = None

    def __init__(self):
        super().__init__()
        self.ble = Ble(self)
        self.daemon = Daemon(self)

    def init(self):
        self.config = Config()

    def on_open(self, sid, data):
        self.init()

        data = json.loads(data)
        self.config.write("version", data["version"])

        if "port" in data:
            self.config.write("port", data["port"])

        if "ble_address" in data:
            self.config.write("ble_address", data["ble_address"])
        else:
            data["ble_address"] = self.config.read("ble_address")

        storage = Storage()
        last = storage.fetch_last_measurement_by_name(data["name"])
        if last:
            now = arrow.now()
            if now.timestamp - int(last["timestamp"]) > 3600:
                match = re.match(".+( [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2})$", data["name"])
                if match:
                    data["name"] = data["name"][:-len(match.group(1))]
                data["name"] += " " + arrow.now().format("YYYY-MM-DD HH:mm")
        self.config.write("name", data["name"])

        try:
            self.config.write("rate", float(data["rate"]))
        except ValueError:
            pass

        if data["version"].startswith("TC") and ("ble_address" not in data or not data["ble_address"]):
            self.daemon.log("BLE address is missing. Select address in Setup")
            return

        self.emit("connecting")
        self.daemon.start()

    def on_scan(self, sid):
        self.init()
        try:
            data = self.ble.scan()
            result = ["Results:"]
            if len(data) == 0:
                result.append("no device found, try again")
            for device in data:
                name = device["address"] + " (" + device["name"] + ")"
                result.append("<a href=\"#\" data-address=\"" + device["address"] + "\">" + name + "</a>")
            self.emit("scan-result", "\n".join(result))

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            logging.exception(sys.exc_info()[0])
            self.emit("scan-result", traceback.format_exc())

    def on_close(self, sid):
        self.init()
        self.emit("disconnecting")
        self.daemon.stop()


class Daemon:
    running = None
    thread = None
    storage = None
    config = None
    interface = None

    def __init__(self, backend):
        self.backed = backend
        self.storage = Storage()
        if self.storage.fetch_status() != "disconnected":
            self.storage.update_status("disconnected")
        self.loop = asyncio.new_event_loop()

    def start(self):
        self.running = True
        if self.thread is None:
            self.thread = Thread(target=self.run)
        if not self.thread.is_alive():
            self.thread.start()

    def stop(self):
        self.log("Disconnecting")
        self.running = False
        if self.interface:
            self.interface.close()
        while self.thread and self.thread.is_alive():
            time.sleep(0.1)
        self.emit("disconnected")

    def run(self):
        self.storage = Storage()
        self.config = Config()

        interface = None
        version = self.config.read("version")
        if version.startswith("TC"):
            ble = True
            self.interface = self.backed.ble
        else:
            ble = False
            self.interface = interface = Interface(port=self.config.read("port"))
            if version == "UM25C":
                interface.enable_higher_resolution()

        try:
            self.log("Connecting")
            if ble:
                self.backed.ble.connect()
            else:
                interface.connect()
            self.emit("connected")
            self.log("Connected")

            while self.running:
                if ble:
                    data = self.backed.ble.read()
                else:
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
            self.emit("log-error")
        finally:
            if ble:
                self.backed.ble.close()
            else:
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

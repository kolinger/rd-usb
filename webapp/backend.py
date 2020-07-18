import asyncio
import json
import logging
import re
import sys
from threading import Thread
from time import time, sleep
import traceback

import arrow
from serial.tools.list_ports import comports
from socketio import Namespace

from interfaces.tc import TcBleInterface
from interfaces.wrapper import Wrapper
from utils.config import Config
from utils.formatting import Format
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

        if "port" in data:
            self.config.write("port", data["port"])

        if "ble_address" in data:
            self.config.write("ble_address", data["ble_address"])
        else:
            data["ble_address"] = self.config.read("ble_address")

        storage = Storage()
        last = storage.fetch_last_measurement_by_name(data["name"])
        if last:
            if time() - int(last["timestamp"]) > 3600:
                match = re.match(".+( [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2})$", data["name"])
                if match:
                    data["name"] = data["name"][:-len(match.group(1))]
                data["name"] += " " + arrow.now().format("YYYY-MM-DD HH:mm")
        self.config.write("name", data["name"])

        try:
            self.config.write("rate", float(data["rate"]))
        except ValueError:
            pass

        tc_ble = data["version"].startswith("TC") and "USB" not in data["version"]
        if tc_ble and ("ble_address" not in data or not data["ble_address"]):
            self.daemon.log("BLE address is missing. Select address in Setup")
            return

        self.emit("connecting")
        self.daemon.start()

    def on_scan_ble(self, sid):
        self.init()
        try:
            result = ["Results:"]

            data = TcBleInterface(self.config.read("ble_address")).scan()
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

    def on_scan_serial(self, sid):
        self.init()
        try:
            result = ["Results:"]

            data = comports()
            if len(data) == 0:
                result.append("no device found, try again")
            else:
                additional = [
                    "description",
                    "manufacturer",
                    "product",
                    "serial_number",
                    "vid",
                    "pid",
                ]

                for device in data:
                    description = []

                    for property in additional:
                        value = getattr(device, property)
                        if value is not None:
                            value = str(value).strip()
                            content = property + ": " + value
                            if property == "description":
                                content = value
                            elif property == "vid":
                                content = "VID_" + hex(int(value))[2:].upper().zfill(4)
                            elif property == "pid":
                                content = "PID_" + hex(int(value))[2:].upper().zfill(4)
                            description.append(content)

                    name = device.device
                    if len(description) > 0:
                        name += " (" + ", ".join(description) + ")"

                    result.append("<a href=\"#\" data-address=\"" + device.device + "\">" + name + "</a>")

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
            self.interface.disconnect()
        while self.thread and self.thread.is_alive():
            sleep(0.1)
        self.emit("disconnected")

    def run(self):
        self.storage = Storage()
        self.config = Config()

        self.interface = Wrapper()

        try:
            self.log("Connecting")
            self.retry(self.interface.connect)
            self.emit("connected")
            self.log("Connected")

            while self.running:
                data = self.retry(self.interface.read)
                if isinstance(data, str):
                    if data == "disconnected":
                        self.disconnect()
                        return
                    raise Exception(data)
                else:
                    self.log(json.dumps(data))
                    if data:
                        data["name"] = self.config.read("name")
                        self.update(data)
                    self.storage.store_measurement(data)
                sleep(self.config.read("rate"))

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            logging.exception(sys.exc_info()[0])
            self.emit("log", traceback.format_exc())
            self.emit("log-error")
        finally:
            self.disconnect()

    def disconnect(self):
        self.interface.disconnect()
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

    def retry(self, callback):
        timeout = time() + 60
        count = 10
        reconnect = False
        while True:
            try:
                if reconnect:
                    self.interface.disconnect()
                    self.interface.connect()
                    # noinspection PyUnusedLocal
                    reconnect = False

                return callback()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                count -= 1
                logging.exception(sys.exc_info()[0])
                if timeout <= time() or count <= 0:
                    raise
                else:
                    self.log("operation failed, retrying")
                    self.emit("log", traceback.format_exc())
                    reconnect = True

    def emit(self, event, data=None):
        if event == "log":
            self.storage.log(data)
        elif event in ["connecting", "connected", "disconnecting", "disconnected"]:
            self.storage.update_status(event)
        self.backed.emit(event, data)

    def log(self, message):
        prefix = arrow.now().format("YYYY-MM-DD HH:mm:ss") + " - "
        self.emit("log", prefix + message + "\n")

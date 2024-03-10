import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from threading import Thread
from time import time, sleep
from timeit import default_timer as timer
import traceback

import bluetooth
import pendulum
from serial.tools.list_ports import comports
from socketio import Namespace

from interfaces.interface import FatalErrorException
from interfaces.tc import TcBleInterface
from interfaces.wrapper import Wrapper
from utils.config import Config
from utils.converter import Converter
from utils.formatting import Format
from utils.storage import Storage


class Backend(Namespace):
    config = None

    def __init__(self, on_receive, on_receive_interval):
        super().__init__()
        self.daemon = Daemon(self, on_receive, on_receive_interval)
        self.handle_auto_connect()

    def handle_auto_connect(self):
        config = Config()
        setup = config.read("setup")
        auto_connect = self.daemon.parse_setup_option(setup, "auto_connect", str, "no")
        if auto_connect == "yes":
            self.on_open(None, config.data)

    def init(self):
        self.config = Config()

    def on_open(self, sid, data):
        self.init()

        if isinstance(data, str):
            data = json.loads(data)

        self.config.write("version", data["version"])

        if "port" in data:
            self.config.write("port", data["port"])

        if "rfcomm_address" in data:
            self.config.write("rfcomm_address", data["rfcomm_address"])
        else:
            data["rfcomm_address"] = self.config.read("rfcomm_address")

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
                data["name"] += " " + pendulum.now().format("YYYY-MM-DD HH:mm")

        if not data["name"]:
            data["name"] = "My measurement"

        self.config.write("name", data["name"])

        try:
            self.config.write("rate", float(data["rate"]))
        except ValueError:
            pass

        rfcomm = data["version"].startswith("UM") and not data["version"].endswith("Serial")
        if rfcomm and ("rfcomm_address" not in data or not data["rfcomm_address"]):
            self.daemon.log("Bluetooth address is missing. Select address in Setup")
            return

        tc_ble = data["version"].startswith("TC") and not data["version"].endswith("USB")
        if tc_ble and ("ble_address" not in data or not data["ble_address"]):
            self.daemon.log("BLE address is missing. Select address in Setup")
            return

        self.emit("connecting")
        self.daemon.start()

    def on_scan_rfcomm(self, sid):
        self.init()
        try:
            result = ["Results:"]

            devices = bluetooth.discover_devices(lookup_names=True)
            if len(devices) == 0:
                result.append("no device found, try again")

            for address, name in devices:
                name = "%s (%s)" % (address, name)
                result.append("<a href=\"#\" data-address=\"%s\">%s</a>" % (address, name))

            self.emit("scan-result", "\n".join(result))

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            logging.exception(sys.exc_info()[0])
            self.emit("scan-result", traceback.format_exc())

    def on_scan_ble(self, sid):
        self.init()
        try:
            result = ["Results:"]

            data = TcBleInterface(self.config.read("ble_address")).scan()
            if len(data) == 0:
                result.append("no device found, try again")

            for device in data:
                name = "%s (%s)" % (device["address"], device["name"])
                result.append("<a href=\"#\" data-address=\"%s\">%s</a>" % (device["address"], name))

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

    def emit(self, event, data=None, to=None, room=None, skip_sid=None, namespace=None, callback=None):
        if self.server is None:
            return
        super().emit(event, data=data, to=to, room=room, skip_sid=skip_sid, namespace=namespace, callback=callback)


class Daemon:
    DEFAULT_TIMEOUT = 60
    DEFAULT_RETRY_COUNT = 10

    running = None
    thread = None
    storage = None
    config = None
    interface = None
    buffer = None
    buffer_expiration = None
    timeout = None
    retry_count = None

    def __init__(self, backend, on_receive, on_receive_interval):
        self.backed = backend
        self.on_receive = on_receive
        self.on_receive_interval = on_receive_interval
        self.storage = Storage()
        if self.storage.fetch_status() != "disconnected":
            self.storage.update_status("disconnected")
        self.loop = asyncio.new_event_loop()
        self.converter = Converter()

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
        self.thread = None

    def run(self):
        self.storage = Storage()
        self.config = Config()

        self.interface = Wrapper()

        setup = self.config.read("setup")
        self.timeout = self.parse_setup_option(setup, "timeout", int, self.DEFAULT_TIMEOUT)
        self.retry_count = self.parse_setup_option(setup, "retry_count", int, self.DEFAULT_RETRY_COUNT)

        try:
            self.log("Connecting")
            self.retry(self.interface.connect)
            self.emit("connected")
            self.log("Connected")

            name = self.config.read("name")
            interval = float(self.config.read("rate"))
            version = self.config.read("version")
            session_id = self.storage.create_session(name, version)
            while self.running:
                begin = timer()
                data = self.retry(self.interface.read)

                if isinstance(data, str):
                    if data in ["disconnected", "connected"]:
                        self.disconnect()
                        return
                    raise Exception(data)
                else:
                    self.log(json.dumps(data))
                    if data:
                        data["session_id"] = session_id
                        self.update(data, version)
                    self.storage.store_measurement(data)

                measurement_runtime = timer() - begin
                sleep_time = interval - measurement_runtime
                if sleep_time > 0:
                    sleep(sleep_time)

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

    def update(self, data, version):
        format = Format(version)

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

        graph = self.converter.convert(graph)

        if self.on_receive:
            if not self.buffer:
                self.buffer = []

            data["timestamp"] = int(data["timestamp"])
            self.buffer.append(data)

            execute = True
            if self.on_receive_interval:
                execute = False
                if not self.buffer_expiration or self.buffer_expiration <= time():
                    execute = True
                    self.buffer_expiration = time() + self.on_receive_interval

            if execute:
                payload = json.dumps(self.buffer)
                self.buffer = None
                payload_file = os.path.join(os.getcwd(), "on-receive-payload-%s.json") % time()
                with open(payload_file, "w") as file:
                    file.write(payload)

                logging.info("executing --on-receive command '%s' with payload file '%s'" % (
                    self.on_receive, payload_file
                ))
                command = self.on_receive + " \"" + payload_file + "\""
                env = os.environ.copy()
                env["PYTHONPATH"] = ""
                subprocess.Popen(command, shell=True, env=env)

        self.emit("update", json.dumps({
            "table": table,
            "graph": graph,
        }))

    def retry(self, callback):
        timeout = self.timeout
        deadline = time() + timeout
        count = self.retry_count

        reconnect = False
        while self.running:
            try:
                if reconnect:
                    self.interface.disconnect()
                    self.interface.connect()
                    # noinspection PyUnusedLocal
                    reconnect = False

                return callback()
            except (KeyboardInterrupt, SystemExit):
                raise
            except FatalErrorException:
                raise
            except:
                count -= 1
                logging.exception(sys.exc_info()[0])

                if self.timeout > 0 and deadline <= time():
                    raise

                if self.retry_count > 0 and count <= 0:
                    raise

                condition = []
                if self.retry_count > 0:
                    condition.append("%s of %s" % (self.retry_count - count, self.retry_count))
                if self.timeout > 0:
                    timestamp = pendulum.from_timestamp(deadline).in_tz("local").format("YYYY-MM-DD HH:mm:ss")
                    condition.append("until %s" % timestamp)

                if len(condition):
                    condition = " or ".join(condition)
                else:
                    condition = "indefinitely"

                self.log("operation failed, retrying %s" % condition)
                self.emit("log", traceback.format_exc())
                reconnect = True

    def emit(self, event, data=None):
        if event == "log":
            self.storage.log(data)
        elif event in ["connecting", "connected", "disconnecting", "disconnected"]:
            self.storage.update_status(event)
        self.backed.emit(event, data)

    def log(self, message):
        prefix = pendulum.now().format("YYYY-MM-DD HH:mm:ss") + " - "
        self.emit("log", prefix + message + "\n")

    def parse_setup_option(self, setup, name, data_type, default=None):
        if isinstance(setup, dict) and name in setup:
            try:
                return data_type(setup[name])
            except (ValueError, TypeError):
                pass
        return default

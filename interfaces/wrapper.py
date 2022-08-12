from multiprocessing import Queue, Process
import queue
from queue import Empty
from time import time
import traceback

from interfaces.interface import Interface
from interfaces.tc import TcBleInterface, TcSerialInterface
from interfaces.um import UmInterface
from utils.config import Config, get_args, initialize_paths_from_args


class Wrapper(Interface):
    listener = None
    process = None

    def __init__(self):
        self.command = Queue()
        self.result = Queue()

    def run(self):
        if self.process is None or not self.process.is_alive():
            self.process = Process(target=self._run, args=(self.command, self.result, get_args()))
            self.process.daemon = True
            self.process.start()

    def _run(self, command, result, args):
        receiver = Receiver(command, result, args)
        receiver.run()

    def connect(self):
        self.run()
        self.command.put("connect")
        self.get_result(60)

    def disconnect(self):
        if not self.process.is_alive():
            return

        self.command.put("disconnect")
        try:
            self.get_result(10)
        except TimeoutError:
            self.process.terminate()

    def read(self):
        self.run()
        self.command.put("read")
        return self.get_result(60)

    def get_result(self, timeout):
        timeout = time() + timeout
        result = None
        while timeout > time():
            try:
                result = self.result.get(block=True, timeout=1)
                break
            except Empty:
                pass

        if result is None:
            raise TimeoutError

        if "Traceback" in result:
            raise ErrorException(result)

        return result


class Receiver:
    def __init__(self, command, result, args):
        self.command = command
        self.result = result
        initialize_paths_from_args(args)

    def run(self):
        config = Config()

        version = config.read("version")
        serialTimeout = int(config.read("serial_timeout", 10))
        if version.startswith("TC"):
            if version.endswith("USB"):
                interface = TcSerialInterface(config.read("port"), serialTimeout)
            else:
                interface = TcBleInterface(config.read("ble_address"))
        else:
            interface = UmInterface(config.read("port"), serialTimeout)
            if version == "UM25C":
                interface.enable_higher_resolution()

        while True:
            try:
                message = self.command.get(block=True, timeout=1)
            except queue.Empty:
                continue

            if message == "connect":
                self.result.put(self.call(interface.connect, "connected"))
            if message == "disconnect":
                self.result.put(self.call(interface.disconnect, "disconnected"))
            if message == "read":
                self.result.put(self.call(interface.read))

    def call(self, callback, default=None):
        try:
            result = callback()
            if result is None:
                return default
            return result
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            return traceback.format_exc()


class ErrorException(Exception):
    pass

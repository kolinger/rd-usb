from multiprocessing import Queue, Process
from queue import Empty
from time import time
import traceback

from interfaces.ble import BleInterface
from interfaces.interface import Interface
from interfaces.regular import RegularInterface
from utils.config import Config


class Wrapper(Interface):
    listener = None
    process = None

    def __init__(self):
        self.command = Queue()
        self.result = Queue()

    def run(self):
        if self.process is None or not self.process.is_alive():
            self.process = Process(target=self._run, args=(self.command, self.result))
            self.process.daemon = True
            self.process.start()

    def _run(self, command, result):
        receiver = Receiver(command, result)
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
        except TimeoutError as e:
            self.process.terminate()
            raise e

    def read(self):
        self.run()
        self.command.put("read")
        return self.get_result(5)

    def get_result(self, timeout):
        timeout = time() + timeout
        result = None
        while timeout > time():
            try:
                result = self.result.get(False)
                break
            except Empty:
                pass

        if result is None:
            raise TimeoutError

        if "Traceback" in result:
            raise ErrorException(result)

        return result


class Receiver:
    def __init__(self, command, result):
        self.command = command
        self.result = result

    def run(self):
        config = Config()

        version = config.read("version")
        if version.startswith("TC"):
            interface = BleInterface(config.read("ble_address"))
        else:
            interface = RegularInterface(config.read("port"))
            if version == "UM25C":
                interface.enable_higher_resolution()

        while True:
            message = self.command.get()
            if message == "connect":
                self.result.put(self.call(interface.connect, "connected"))
            if message == "disconnect":
                self.result.put(self.call(interface.disconnect, "disconnected"))
            if message == "read":
                self.result.put(self.call(interface.read))

    def call(self, callback, default=None):
        while True:
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

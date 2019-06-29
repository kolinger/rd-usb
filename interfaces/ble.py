import asyncio
from time import time, sleep

from Crypto.Cipher import AES
from bleak import BleakClient
from bleak import discover

from interfaces.interface import Interface

SERVER_RX_DATA = "0000ffe9-0000-1000-8000-00805f9b34fb"
SERVER_TX_DATA = "0000ffe4-0000-1000-8000-00805f9b34fb"
ASK_FOR_VALUES_COMMAND = "bgetva"


class BleInterface(Interface):
    timeout = 30
    client = None
    loop = None
    bound = False

    def __init__(self, address):
        self.address = address
        self.response = Response()

    def scan(self):
        async def run():
            devices = await discover()
            formatted = []
            for device in devices:
                formatted.append({
                    "address": device.address,
                    "name": device.name,
                })
            return formatted

        return self.get_loop().run_until_complete(run())

    def connect(self):
        self.get_loop().run_until_complete(self._connect_run(self.address))

    async def _connect_run(self, address):
        self.client = BleakClient(address, loop=self.get_loop())
        await self.client.connect()

    def disconnect(self):
        expiration = time() + self.timeout
        while self.loop.is_running() and time() <= expiration:
            sleep(0.1)

        sleep(1)

        try:
            self.get_loop().run_until_complete(self._close_run())
        except RuntimeError as e:
            if "loop is already running" not in str(e):
                raise e

        self.bound = False

    async def _close_run(self):
        try:
            await self.client.stop_notify(SERVER_TX_DATA)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass

        try:
            await self.client.disconnect()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass

    def read(self):
        return self.get_loop().run_until_complete(self._read_run())

    async def _read_run(self):
        self.response.reset()

        for retry in range(0, 3):
            await self.client.write_gatt_char(SERVER_RX_DATA, self.encode_command(ASK_FOR_VALUES_COMMAND))

            if not self.bound:
                self.bound = True
                await self.client.start_notify(SERVER_TX_DATA, self.response.callback)

            expiration = time() + self.timeout
            while not self.response.is_complete() and time() <= expiration:
                sleep(0.1)

            if not self.response.is_complete():
                continue

            break

        if not self.response.is_complete():
            raise NoResponseException

        return self.response.decode()

    def encode_command(self, command):
        return (command + "\r\n").encode("ascii")

    def get_loop(self):
        if not self.loop:
            self.loop = asyncio.new_event_loop()
        return self.loop


class Response:
    key = [
        88, 33, -6, 86, 1, -78, -16, 38,
        -121, -1, 18, 4, 98, 42, 79, -80,
        -122, -12, 2, 96, -127, 111, -102, 11,
        -89, -15, 6, 97, -102, -72, 114, -120
    ]
    buffer = bytearray()
    index = 0

    def callback(self, sender, data):
        self.buffer.extend(data)
        self.index += len(data)

    def is_complete(self):
        return self.index >= 192

    def decrypt(self):
        key = []
        for index, value in enumerate(self.key):
            key.append(value & 255)

        aes = AES.new(bytes(key), AES.MODE_ECB)
        return aes.decrypt(self.buffer)

    def decode(self):
        data = self.decrypt()

        if self.decode_integer(data, 88) == 1:
            temperature_multiplier = -1
        else:
            temperature_multiplier = 1

        return {
            "timestamp": time(),
            "voltage": self.decode_integer(data, 48, 10000),
            "current": self.decode_integer(data, 52, 100000),
            "power": self.decode_integer(data, 56, 10000),
            "resistance": self.decode_integer(data, 68, 10),
            "accumulated_current": self.decode_integer(data, 72),
            "accumulated_power": self.decode_integer(data, 76),
            "accumulated_time": None,
            "temperature": self.decode_integer(data, 92) * temperature_multiplier,
            "data_plus": self.decode_integer(data, 96, 100),
            "data_minus": self.decode_integer(data, 100, 100),
            "mode_id": None,
            "mode_name": None
        }

    def decode_integer(self, data, first_byte, divider=1):
        temp4 = data[first_byte] & 255
        temp3 = data[first_byte + 1] & 255
        temp2 = data[first_byte + 2] & 255
        temp1 = data[first_byte + 3] & 255
        return ((((temp1 << 24) | (temp2 << 16)) | (temp3 << 8)) | temp4) / float(divider)

    def reset(self):
        self.buffer = bytearray()
        self.index = 0


class NoResponseException(Exception):
    pass

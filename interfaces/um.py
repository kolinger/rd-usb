import codecs
from collections import OrderedDict
from time import time

import serial

from interfaces.interface import Interface


class UmInterface(Interface):
    serial = None
    higher_resolution = False
    modes = {
        0: "Unknown",
        1: "QC2.0",
        2: "QC3.0",
        3: "APP2.4A",
        4: "APP2.1A",
        5: "APP1.0A",
        6: "APP0.5A",
        7: "DCP1.5A",
        8: "SAMSUNG",
        65535: "Unknown"
    }

    def __init__(self, port, timeout):
        self.port = port
        self.timeout = timeout

    def enable_higher_resolution(self):
        self.higher_resolution = True

    def connect(self):
        if self.serial is None:
            self.serial = serial.Serial(port=self.port, baudrate=9600, timeout=self.timeout, write_timeout=0)

    def read(self):
        self.open()
        self.send("f0")
        data = self.serial.read(130)
        return self.parse(data)

    def send(self, value):
        self.open()
        self.serial.write(bytes.fromhex(value))

    def parse(self, data):
        if len(data) < 130:
            return None

        data = codecs.encode(data, "hex").decode("utf-8")

        result = OrderedDict()

        multiplier = 10 if self.higher_resolution else 1

        result["timestamp"] = time()
        result["voltage"] = int("0x" + data[4] + data[5] + data[6] + data[7], 0) / (100 * multiplier)
        result["current"] = int("0x" + data[8] + data[9] + data[10] + data[11], 0) / (1000 * multiplier)
        result["power"] = int("0x" + data[12] + data[13] + data[14] + data[15] + data[16] +
                              data[17] + data[18] + data[19], 0) / 1000
        result["temperature"] = int("0x" + data[20] + data[21] + data[22] + data[23], 0)
        result["data_plus"] = int("0x" + data[192] + data[193] + data[194] + data[195], 0) / 100
        result["data_minus"] = int("0x" + data[196] + data[197] + data[198] + data[199], 0) / 100
        result["mode_id"] = int("0x" + data[200] + data[201] + data[202] + data[203], 0)
        result["mode_name"] = None
        result["accumulated_current"] = int("0x" + data[204] + data[205] + data[206] + data[207] + data[208] +
                                            data[209] + data[210] + data[211], 0)
        result["accumulated_power"] = int("0x" + data[212] + data[213] + data[214] + data[215] + data[216] +
                                          data[217] + data[218] + data[219], 0)
        result["accumulated_time"] = int("0x" + data[224] + data[225] + data[226] + data[227] + data[228] +
                                         data[229] + data[230] + data[231], 0)
        result["resistance"] = int("0x" + data[244] + data[245] + data[246] + data[247] + data[248] +
                                   data[249] + data[250] + data[251], 0) / 10

        if result["mode_id"] in self.modes:
            result["mode_name"] = self.modes[result["mode_id"]]

        return result

    def open(self):
        if not self.serial.isOpen():
            self.serial.open()

    def disconnect(self):
        if self.serial:
            self.serial.close()

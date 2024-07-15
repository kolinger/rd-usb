import decimal

import pendulum

from utils.usb import decode_usb_data_lines


class Format:
    time_format = "YYYY-MM-DD HH:mm:ss"
    table_fields = ["time", "voltage", "current", "power", "temperature", "data", "mode", "accumulated", "resistance"]
    graph_fields = [
        "timestamp", "voltage", "current", "power", "temperature",
        "resistance", "accumulated_current", "accumulated_power",
    ]
    export_fields = [
        "time",
        "voltage",
        "current",
        "power",
        "temperature",
        "data_plus",
        "data_minus",
        "resistance",
        "accumulated_current",
        "accumulated_power",
        "accumulated_time",
        "run_time",
        "run_time_seconds",
        "timestamp",
        "zeroed_accumulated_current",
        "zeroed_accumulated_power",
        "zeroed_accumulated_time",
    ]
    field_names = {
        "time": "Time",
        "voltage": "Voltage (V)",
        "current": "Current (A)",
        "power": "Power (W)",
        "temperature": "Temperature (°C)",
        "data_plus": "Data+ (V)",
        "data_minus": "Data- (V)",
        "resistance": "Resistance (Ω)",
        "accumulated_current": "Accumulated current (mAh)",
        "accumulated_power": "Accumulated power (mWh)",
        "accumulated_time": "Accumulated time (seconds)",
        "run_time": "Run time",
        "run_time_seconds": "Run time (seconds)",
        "timestamp": "Unix time",
        "zeroed_accumulated_current": "Zerod accumulated current (mAh)",
        "zeroed_accumulated_power": "Zerod accumulated power (mWh)",
        "zeroed_accumulated_time": "Zerod accumulated time (seconds)",
    }

    def __init__(self, version=None):
        self.version = version
        self.um25c = self.version == "UM25C"
        self.tc66c = self.version and self.version.startswith("TC66C")
        self.decimal_context = decimal.Context(20)

    def time(self, data):
        time = pendulum.from_timestamp(data["timestamp"])
        time = time.in_tz("local")
        return time.format(self.time_format)

    def timestamp(self, data):
        return data["timestamp"] * 1000

    def voltage(self, data):
        return self.format_value(data, "voltage") + " V"

    def current(self, data):
        return self.format_value(data, "current") + " A"

    def power(self, data):
        return self.format_value(data, "power") + " W"

    def temperature(self, data):
        return self.format_value(data, "temperature") + " °C"

    def data(self, data):
        return "+" + self.format_value(data, "data_plus") + " / -" + self.format_value(data, "data_minus") + " V"

    def mode(self, data):
        if data["mode_id"] is None and data["data_plus"] is not None:
            return decode_usb_data_lines(data["data_plus"], data["data_minus"])
        if data["mode_name"]:
            return data["mode_name"]
        return "id: " + str(data["mode_id"])

    def accumulated_current(self, data):
        return self.format_value(data, "accumulated_current") + " mAh"

    def accumulated_power(self, data):
        return self.format_value(data, "accumulated_power") + " mWh"

    def accumulated_time(self, data):
        if data["accumulated_time"] is None:
            return ""
        return str(data["accumulated_time"]) + " seconds"

    def accumulated(self, data):
        parts = [
            self.accumulated_current(data),
            self.accumulated_power(data),
        ]
        if data["accumulated_time"] is not None:
            parts.append(self.accumulated_time(data))
        return " / ".join(parts)

    def zeroed_accumulated_current(self, data):
        return self.format_value(data, "zeroed_accumulated_current") + " mAh"

    def zeroed_accumulated_power(self, data):
        return self.format_value(data, "zeroed_accumulated_power") + " mWh"

    def zeroed_accumulated_time(self, data):
        if data["zeroed_accumulated_time"] is None:
            return ""
        return str(data["zeroed_accumulated_time"]) + " seconds"

    def zeroed_accumulated(self, data):
        parts = [
            self.zeroed_accumulated_current(data),
            self.zeroed_accumulated_power(data),
        ]
        if data["zeroed_accumulated_time"] is not None:
            parts.append(self.zeroed_accumulated_time(data))
        return " / ".join(parts)

    def resistance(self, data):
        return str(data["resistance"]) + " Ω"

    def field_name(self, field):
        if field in self.field_names:
            return self.field_names[field]
        return field

    def field_name_reverse(self, alias):
        for field_name, field_alias in self.field_names.items():
            if field_alias == alias:
                return field_name
        print(alias)
        return None

    def format_value(self, data, name):
        value = data[name]
        precision = None
        variable = False
        if name == "voltage":
            if self.tc66c:
                precision = 4
            elif self.um25c:
                precision = 3
            else:
                precision = 2
            variable = True
        elif name == "current":
            if self.tc66c:
                precision = 5
            elif self.um25c:
                precision = 4
            else:
                precision = 3
            variable = True
        elif name == "power":
            precision = 4 if self.tc66c else 3
            variable = True
        elif name == "temperature":
            precision = 0
        elif name in ["data_plus", "data_minus"]:
            precision = 2
        elif name in ["accumulated_current", "accumulated_power"]:
            precision = 0
        elif name in ["zeroed_accumulated_current", "zeroed_accumulated_power"]:
            precision = 0
        elif name == "resistance":
            precision = 1
        if precision is not None:
            if not self.version and variable:
                # backward compatibility:
                # since we don't know what meter was used, then don't round to fixed number of places
                value = format(self.decimal_context.create_decimal(repr(value)), "f")
            else:
                value = self.format_number(value, precision)
        return value

    def format_number(self, value, precision):
        if precision > 0:
            return ("{:.%sf}" % precision).format(value)
        return "{:d}".format(int(round(value)))

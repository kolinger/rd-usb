import pendulum

from utils.usb import decode_usb_data_lines


class Format:
    table_fields = ["time", "voltage", "current", "power", "temperature", "data", "mode", "accumulated", "resistance"]
    graph_fields = [
        "timestamp", "voltage", "current", "power", "temperature",
        "resistance", "accumulated_current", "accumulated_power",
    ]
    export_fields = [
        "time", "voltage", "current", "power", "temperature", "data_plus", "data_minus", "resistance",
        "accumulated_current", "accumulated_power", "accumulated_time", "run_time", "run_time_seconds", "timestamp",
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
    }

    def __init__(self):
        pass

    def time(self, data):
        time = pendulum.from_timestamp(data["timestamp"])
        time = time.in_tz("local")
        return time.format("YYYY-MM-DD HH:mm:ss")

    def timestamp(self, data):
        return data["timestamp"] * 1000

    def voltage(self, data):
        return str(data["voltage"]) + " V"

    def current(self, data):
        return str(data["current"]) + " A"

    def power(self, data):
        return str(data["power"]) + " W"

    def temperature(self, data):
        return str(data["temperature"]) + " °C"

    def data(self, data):
        return "+" + str(data["data_plus"]) + " / -" + str(data["data_minus"]) + " V"

    def mode(self, data):
        if data["mode_id"] is None and data["data_plus"] is not None:
            return decode_usb_data_lines(data["data_plus"], data["data_minus"])
        if data["mode_name"]:
            return data["mode_name"]
        return "id: " + str(data["mode_id"])

    def accumulated_current(self, data):
        return str(data["accumulated_current"]) + " mAh"

    def accumulated_power(self, data):
        return str(data["accumulated_power"]) + " mWh"

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

    def resistance(self, data):
        return str(data["resistance"]) + " Ω"

    def field_name(self, field):
        if field in self.field_names:
            return self.field_names[field]
        return field

import arrow
from dateutil import tz


class Format:
    table_fields = ["time", "voltage", "current", "power", "temperature", "data", "mode", "accumulated", "resistance"]
    graph_fields = [
        "timestamp", "voltage", "current", "power", "temperature",
        "resistance", "accumulated_current","accumulated_power"
    ]

    def __init__(self):
        pass

    def time(self, data):
        time = arrow.get(data["timestamp"])
        time = time.replace(tzinfo=tz.gettz("UTC")).to(tz=tz.gettz("Europe/Prague"))
        return time.format("DD.MM.YYYY HH:mm:ss")

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
        if data["mode_name"]:
            return data["mode_name"]
        return "id: " + str(data["mode_id"])

    def accumulated_current(self, data):
        return str(data["accumulated_current"]) + " mAh"

    def accumulated_power(self, data):
        return str(data["accumulated_power"]) + " mWh"

    def accumulated_time(self, data):
        return str(data["accumulated_time"]) + " seconds"

    def accumulated(self, data):
        parts = [
            self.accumulated_current(data),
            self.accumulated_power(data),
            self.accumulated_time(data),
        ]
        return " / ".join(parts)

    def resistance(self, data):
        return str(data["resistance"]) + " Ω"

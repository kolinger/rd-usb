data_line_voltages = [
    {
        "name": "Apple 0.5A",
        "positive": 2,
        "negative": 2,
    },
    {
        "name": "Apple 1.0A",
        "positive": 2,
        "negative": 2.7,
    },
    {
        "name": "Apple 2.1A",
        "positive": 2.7,
        "negative": 2,
    },
    {
        "name": "Apple 2.4A",
        "positive": 2.7,
        "negative": 2.7,
    },
    {
        "name": "Samsung 0.9A",
        "positive": 1.7,
        "negative": 1.7,
    },
    {
        "name": "Quick Charge",
        "values": [
            {"positive": 0.6, "negative": 0},  # 5V
            {"positive": 3.3, "negative": 0.6},  # 9V
            {"positive": 0.6, "negative": 0.6},  # 12V
            {"positive": 3.3, "negative": 3.3},  # 20V
        ],
    },
    {
        "name": "DCP 1.5A",
        "equal": True,
    }
]


def decode_usb_data_lines(positive, negative):
    for data in data_line_voltages:
        if "equal" in data:
            if compare_voltage(positive, negative):
                return data["name"]

        elif "values" in data:
            for pair in list(data["values"]):
                if compare_voltage(positive, pair["positive"]) and compare_voltage(negative, pair["negative"]):
                    return data["name"]

        elif compare_voltage(positive, data["positive"]) and compare_voltage(negative, data["negative"]):
            return data["name"]

    return "Unknown"


def compare_voltage(value, reference, tolerance=5):
    if value > 2.7:
        tolerance = 15
    minimum = reference * (100 - tolerance) / 100
    maximum = reference * (100 + tolerance) / 100
    return value >= minimum and value <= maximum

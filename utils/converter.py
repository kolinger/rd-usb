class Converter:
    def convert(self, item):
        item["current-m"] = round(item["current"] * 1000)
        return item

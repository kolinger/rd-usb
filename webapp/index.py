import os

import arrow
from flask import url_for, request, jsonify
from flask.blueprints import Blueprint
from flask.templating import render_template

from utils.config import project_root, Config
from utils.formatting import Format
from utils.storage import Storage


class Index:
    config = None
    storage = None

    def __init__(self):
        pass

    def register(self):
        blueprint = Blueprint("index", __name__, template_folder="templates")
        blueprint.add_url_rule("/", "default", self.render_default)
        blueprint.add_url_rule("/data", "data", self.render_data)
        blueprint.add_url_rule("/graph", "graph", self.render_graph)
        blueprint.add_url_rule("/graph.json", "graph_data", self.render_graph_data)
        blueprint.context_processor(self.fill)
        return blueprint

    def init(self):
        self.config = Config()
        self.storage = Storage()

    def fill(self):
        variables = {
            "format": Format(),
            "url_for": self.url_for,
            "port": self.config.read("port", ""),
            "rate": str(self.config.read("rate", 1.0)),
            "name": self.config.read("name", arrow.now().format("YYYY-MM-DD")),
        }

        status = self.storage.fetch_status()
        variables["status"] = status.title()
        variables["connect_disabled"] = status != "disconnected"
        variables["connect_button"] = "Connect" if status == "disconnected" else "Disconnect"

        return variables

    def render_default(self):
        self.init()
        log = self.storage.fetch_log()
        return render_template("default.html", log=log, page="default")

    def render_data(self):
        self.init()

        names, selected = self.prepare_selection()
        measurements = self.storage.fetch_measurements(selected)

        return render_template(
            "data.html",
            names=names,
            selected=selected,
            measurements=measurements,
            page="data"
        )

    def render_graph(self):
        self.init()

        names, selected = self.prepare_selection()

        last_measurement = None
        if selected == "current":
            last_measurement = self.storage.fetch_last_measurement()

        return render_template(
            "graph.html",
            names=names,
            selected=selected,
            item=last_measurement,
            left_axis="voltage",
            right_axis="current",
            page="graph"
        )

    def render_graph_data(self):
        self.init()

        name = request.args.get("name")
        left_axis = request.args.get("left_axis")
        right_axis = request.args.get("right_axis")

        data = {
            "labels": [],
            "left": {
                "data": [],
            },
            "right": {
                "data": [],
            },
        }

        format = Format()
        for item in self.storage.fetch_measurements(name):
            if left_axis in item:
                data["left"]["data"].append({
                    "t": format.timestamp(item),
                    "y": item[left_axis],
                })
            if right_axis in item:
                data["right"]["data"].append({
                    "t": format.timestamp(item),
                    "y": item[right_axis],
                })

        return jsonify(data)

    def prepare_selection(self):
        names = self.storage.fetch_measurement_names()
        selected = request.args.get("name")
        if not selected:
            selected = "current"

        return names, selected

    def url_for(self, endpoint, **values):
        if endpoint == "static":
            filename = values.get("filename", None)
            if filename:
                file_path = os.path.join(project_root, endpoint, filename)
                values["v"] = int(os.stat(file_path).st_mtime)
        return url_for(endpoint, **values)

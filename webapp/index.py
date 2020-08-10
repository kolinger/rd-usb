import csv
import io
from math import ceil
import os

import arrow
from flask import url_for, request, jsonify, redirect, flash, make_response
from flask.blueprints import Blueprint
from flask.templating import render_template

from utils.config import Config, static_path
from utils.formatting import Format
from utils.storage import Storage
from utils.version import version


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
        blueprint.add_url_rule("/ble", "ble", self.render_ble)
        blueprint.add_url_rule("/serial", "serial", self.render_serial)
        blueprint.context_processor(self.fill)
        return blueprint

    def init(self):
        self.config = Config()
        self.storage = Storage()

    def fill(self):
        variables = {
            "rd_user_version": version,
            "format": Format(),
            "url_for": self.url_for,
            "version": self.config.read("version", "UM34C"),
            "port": self.config.read("port", ""),
            "rate": str(self.config.read("rate", 1.0)),
            "name": self.config.read("name", arrow.now().format("YYYY-MM-DD")),
            "ble_address": self.config.read("ble_address"),
        }

        status = self.storage.fetch_status()
        variables["status"] = status.title()
        variables["connect_disabled"] = status != "disconnected"
        variables["connect_button"] = "Connect" if status == "disconnected" else "Disconnect"

        return variables

    def render_default(self):
        self.init()
        self.storage.clear_log()
        log = self.storage.fetch_log()
        return render_template("default.html", log=log, page="default")

    def render_data(self):
        self.init()

        names, selected = self.prepare_selection()
        name = self.storage.translate_selected_name(selected)

        if request.args.get("export") == "":
            string = io.StringIO()
            writer = csv.writer(string)
            format = Format()

            names = []
            for field in format.export_fields:
                names.append(format.field_name(field))
            writer.writerow(names)

            for item in self.storage.fetch_measurements(name):
                values = []
                for field in format.export_fields:
                    if field == "time":
                        values.append(format.time(item))
                    else:
                        values.append(item[field])
                writer.writerow(values)

            output = make_response(string.getvalue())
            output.headers["Content-Disposition"] = "attachment; filename=" + name + ".csv"
            output.headers["Content-type"] = "text/csv"
            return output

        elif request.args.get("destroy") == "":
            self.storage.destroy_measurements(name)
            flash("Measurements with session name '" + name + "' were deleted", "danger")
            return redirect(request.path)

        page = request.args.get("page", 1, int)
        limit = 100
        offset = limit * (page - 1)
        count = self.storage.fetch_measurements_count(name)
        pages = self.prepare_pages(name, page, limit, count)

        measurements = self.storage.fetch_measurements(name, limit, offset)

        return render_template(
            "data.html",
            names=names,
            selected=selected,
            measurements=measurements,
            page="data",
            pages=pages,
        )

    def prepare_pages(self, name, page, limit, count, blocks=10):
        first_page = 1
        related = 3
        last_page = int(ceil(count / limit))
        steps = set(range(max((first_page, page - related)), min((last_page, page + related)) + 1))
        quotient = (last_page - 1) / blocks
        if len(steps) > 1:
            for index in range(0, blocks):
                steps.add(round(quotient * index) + first_page)
        steps.add(last_page)
        steps = sorted(steps)

        pages = []
        for number in steps:
            pages.append({
                "number": number,
                "link": url_for("index.data", page=number, name=name),
                "current": number == page,
            })

        return pages

    def render_graph(self):
        self.init()

        names, selected = self.prepare_selection()

        last_measurement = None
        if selected == "":
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

        selected = request.args.get("name")
        name = self.storage.translate_selected_name(selected)

        left_axis = request.args.get("left_axis")
        right_axis = request.args.get("right_axis")

        format = Format()

        data = []
        for item in self.storage.fetch_measurements(name):
            if left_axis in item:
                data.append({
                    "date": format.timestamp(item),
                    "left": item[left_axis],
                    "right": item[right_axis],
                })

        return jsonify(data)

    def prepare_selection(self):
        names = self.storage.fetch_measurement_names()
        selected = request.args.get("name")
        if not selected:
            selected = ""

        return names, selected

    def fill_config_from_parameters(self):
        value = request.args.get("version")
        if value is not None:
            self.config.write("version", value)

        value = request.args.get("name")
        if value is not None:
            self.config.write("name", value)

        value = request.args.get("rate")
        if value is not None:
            self.config.write("rate", float(value))

    def render_ble(self):
        self.init()
        self.fill_config_from_parameters()
        return render_template(
            "ble.html"
        )

    def render_serial(self):
        self.init()
        self.fill_config_from_parameters()
        return render_template(
            "serial.html"
        )

    def url_for(self, endpoint, **values):
        if endpoint == "static":
            filename = values.get("filename", None)
            if filename:
                file_path = static_path + "/" + filename
                values["v"] = int(os.stat(file_path).st_mtime)
        return url_for(endpoint, **values)

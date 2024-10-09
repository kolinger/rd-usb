import csv
import io
from math import ceil, floor
import os
import pathlib
from time import time
import traceback

from flask import url_for, request, jsonify, redirect, flash, make_response, current_app
from flask.blueprints import Blueprint
from flask.templating import render_template
import pendulum
from werkzeug.utils import secure_filename

from interfaces.tc import TcSerialInterface
from utils.config import Config, static_path, get_data_path
from utils.formatting import Format
from utils.storage import Storage
from utils.version import version
from webapp.backend import Daemon


class Index:
    config = None
    storage = None
    import_in_progress = False

    def register(self):
        blueprint = Blueprint("index", __name__, template_folder="templates")
        blueprint.add_url_rule("/", "default", self.render_default)
        blueprint.add_url_rule("/data", "data", self.render_data)
        blueprint.add_url_rule("/graph", "graph", self.render_graph)
        blueprint.add_url_rule("/graph.json", "graph_data", self.render_graph_data)
        blueprint.add_url_rule("/setup", "setup", self.render_setup, methods=["GET", "POST"])
        blueprint.add_url_rule("/rfcomm", "rfcomm", self.render_rfcomm)
        blueprint.add_url_rule("/ble", "ble", self.render_ble)
        blueprint.add_url_rule("/serial", "serial", self.render_serial)
        blueprint.add_url_rule("/tc66c-import", "tc66c_import", self.render_tc66c_import, methods=["GET", "POST"])
        blueprint.add_url_rule("/csv-import", "csv_import", self.render_csv_import, methods=["GET", "POST"])
        blueprint.context_processor(self.fill)
        return blueprint

    def init(self):
        self.config = Config()
        self.storage = Storage()

    def fill(self):
        variables = {
            "rd_user_version": version,
            "url_for": self.url_for,
            "version": self.config.read("version", "UM34C"),
            "port": self.config.read("port", ""),
            "rate": str(self.config.read("rate", 1.0)),
            "name": self.config.read("name", pendulum.now().format("YYYY-MM-DD")),
            "rfcomm_address": self.config.read("rfcomm_address"),
            "ble_address": self.config.read("ble_address"),
            "format_datetime": self.format_date,
            "app_prefix": current_app.config["app_prefix"]
        }

        status = self.storage.fetch_status()
        variables["status"] = status.title()
        variables["connect_disabled"] = status != "disconnected"
        variables["connect_button"] = "Connect" if status == "disconnected" else "Disconnect"

        setup = self.config.read("setup")
        variables["theme"] = setup["theme"] if setup and "theme" in setup else "light"

        variables["embedded"] = current_app.config["embedded"]

        return variables

    def render_default(self):
        self.init()
        self.storage.clear_log()
        log = self.storage.fetch_log()
        return render_template("default.html", log=log, page="default")

    def render_data(self):
        self.init()

        sessions, selected = self.prepare_selection()
        session = self.storage.get_selected_session(selected)

        format = None
        measurements = []
        pages = []
        if session:
            format = Format(session["version"])

            if request.args.get("export") == "":
                string = io.StringIO()
                writer = csv.writer(string)

                names = []
                for field in format.export_fields:
                    names.append(format.field_name(field))
                writer.writerow(names)

                run_time_offset = None
                for item in self.storage.fetch_measurements(session["id"], zeroed=True):
                    if run_time_offset is None and item["resistance"] < 9999.9:
                        run_time_offset = item["timestamp"]

                    rune_time = 0
                    if run_time_offset is not None:
                        rune_time = round(item["timestamp"] - run_time_offset)

                    values = []
                    for field in format.export_fields:
                        if field == "time":
                            values.append(format.time(item))
                        elif field == "run_time":
                            remaining = rune_time
                            hours = floor(remaining / 3600)
                            remaining -= hours * 3600
                            minutes = floor(remaining / 60)
                            remaining -= minutes * 60
                            seconds = remaining
                            parts = [
                                hours,
                                minutes,
                                seconds,
                            ]
                            for index, value in enumerate(parts):
                                parts[index] = str(value).zfill(2)
                            values.append(":".join(parts))
                        elif field == "run_time_seconds":
                            values.append(rune_time)
                        else:
                            values.append(item[field])
                    writer.writerow(values)

                output = make_response(string.getvalue())
                output.headers["Content-Disposition"] = "attachment; filename=" + session["name"] + ".csv"
                output.headers["Content-type"] = "text/csv"
                return output

            elif request.args.get("destroy") == "":
                if selected == "":
                    flash("Please select session first", "info")
                    return redirect(request.base_url)
                self.storage.destroy_measurements(session["id"])
                flash("Measurements with session name '" + session["name"] + "' were deleted", "danger")
                return redirect(request.base_url)

            page = request.args.get("page", 1, int)
            limit = 100
            offset = limit * (page - 1)
            count = self.storage.fetch_measurements_count(session["id"])
            pages = self.prepare_pages(session["id"], page, limit, count)

            measurements = self.storage.fetch_measurements(session["id"], limit, offset, zeroed=True)

        return render_template(
            "data.html",
            format=format,
            sessions=sessions,
            selected=selected,
            measurements=measurements,
            pages=pages,
            page="data",
            accumulated="zeroed" if request.cookies.get("accumulated") == "zeroed" else "actual"
        )

    def prepare_pages(self, session_id, page, limit, count, blocks=10):
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
                "link": url_for("index.data", page=number, session=session_id),
                "current": number == page,
            })

        return pages

    def render_graph(self):
        self.init()

        sessions, selected = self.prepare_selection()
        session = self.storage.get_selected_session(selected)

        format = Format(session["version"] if session else None)

        last_measurement = None
        if selected == "":
            last_measurement = self.storage.fetch_last_measurement()

        metrics = {
            "voltage": "Voltage (V)",
            "current": "Current (A)",
            "current-m": "Current (mA)",
            "power": "Power (W)",
            "temperature": "Temperature (°C)",
            "accumulated_current": "Accumulated current (mAh)",
            "accumulated_power": "Accumulated power (mWh)",
            "zeroed_accumulated_current": "Accumulated current (mAh) [zeroed]",
            "zeroed_accumulated_power": "Accumulated power (mWh) [zeroed]",
            "resistance": "Resistance (Ω)",
        }

        left_axis = request.args.get("left_axis", default="voltage")
        right_axis = request.args.get("right_axis", default="current")

        return render_template(
            "graph.html",
            format=format,
            sessions=sessions,
            selected=selected,
            item=last_measurement,
            metrics=metrics,
            left_axis=left_axis,
            right_axis=right_axis,
            colors=self.config.read("colors", "colorful"),
            page="graph"
        )

    def render_graph_data(self):
        self.init()

        selected = request.args.get("session")
        session = self.storage.get_selected_session(selected)

        left_axis = request.args.get("left_axis")
        right_axis = request.args.get("right_axis")
        colors = request.args.get("colors")
        if self.config.read("colors") != colors:
            self.config.write("colors", colors, flush=True)

        format = Format(session["version"] if session else None)

        data = []
        if session:
            for item in self.storage.fetch_measurements(session["id"], zeroed=True):
                if left_axis in item and right_axis in item:
                    data.append({
                        "date": format.timestamp(item),
                        "left": item[left_axis],
                        "right": item[right_axis],
                    })

        return jsonify(data)

    def prepare_selection(self):
        sessions = self.storage.fetch_sessions()
        selected = request.args.get("session")
        try:
            selected = int(selected)
        except (ValueError, TypeError):
            selected = None

        if selected is None:
            selected = ""

        return sessions, selected

    def fill_config_from_parameters(self):
        value = request.args.get("version")
        if value is not None:
            self.config.write("version", value)

        value = request.args.get("rate")
        if value is not None:
            self.config.write("rate", float(value))

    def render_setup(self):
        self.init()
        setup: dict = self.config.read("setup")
        if not isinstance(setup, dict):
            setup = {}

        defaults = {
            "theme": "light",
            "auto_connect": "no",
            "timeout": Daemon.DEFAULT_TIMEOUT,
            "retry_count": Daemon.DEFAULT_RETRY_COUNT,
        }

        for name, default_value in defaults.items():
            if name not in setup or setup[name] is None or setup[name] == "":
                setup[name] = default_value

        if "do" in request.form:
            for name in defaults.keys():
                setup[name] = request.form[name]
            self.config.write("setup", setup)
            flash("Settings were successfully saved", "success")
            return redirect(url_for("index.setup"))

        return render_template(
            "setup.html",
            setup=setup,
            page="setup",
            default_timeout=Daemon.DEFAULT_TIMEOUT,
            default_retry_count=Daemon.DEFAULT_RETRY_COUNT,
        )

    def render_rfcomm(self):
        self.init()
        self.fill_config_from_parameters()
        return render_template(
            "rfcomm.html"
        )

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

    def render_tc66c_import(self):
        self.init()
        self.fill_config_from_parameters()

        messages = []
        if self.config.read("version") not in ["TC66C-USB"]:
            messages.append("Available only for TC66C USB")
        elif self.storage.fetch_status() != "disconnected":
            messages.append("Disconnect first")

        session_name = "My recording"
        period = 1
        calculate = False
        if "do" in request.form:
            if len(messages) == 0:
                session_name = request.form.get("session_name")
                if not session_name:
                    messages.append("Please provide session name")

                try:
                    period = int(request.form.get("period"))
                    if period < 1 or period > 60:
                        raise ValueError
                except ValueError:
                    messages.append("Period has invalid value, please enter number between 1 and 60")

                calculate = request.form.get("calculate") is not None

                if len(messages) == 0:
                    messages.extend(self.do_tc66c_import(session_name, period, calculate))
                    if len(messages) == 0:
                        return redirect(url_for("index.graph"))

        return render_template(
            "tc66c-import.html",
            messages=messages,
            session_name=session_name,
            period=period,
            calculate=calculate,
            page="data"
        )

    def do_tc66c_import(self, name, period=1, calculate=False):
        messages = []
        if self.import_in_progress:
            messages.append("Import is already running")
            return messages
        self.import_in_progress = True
        serial_timeout = int(self.config.read("serial_timeout", 10))
        interface = TcSerialInterface(self.config.read("port"), serial_timeout)
        self.storage.fetch_status()
        try:
            interface.connect()
            begin = time()
            previous_timestamp = None
            accumulated_current = 0
            accumulated_power = 0
            session_id = None
            for index, record in enumerate(interface.read_records()):
                timestamp = begin + (index * period)

                if session_id is None:
                    session_id = self.storage.create_session(name, "TC66C recording")

                data = {
                    "timestamp": timestamp,
                    "voltage": round(record["voltage"] * 10000) / 10000,
                    "current": round(record["current"] * 100000) / 100000,
                    "power": 0,
                    "temperature": 0,
                    "data_plus": 0,
                    "data_minus": 0,
                    "mode_id": 0,
                    "mode_name": None,
                    "accumulated_current": round(accumulated_current),
                    "accumulated_power": round(accumulated_power),
                    "accumulated_time": 0,
                    "resistance": 0,
                    "session_id": session_id,
                }

                if calculate:
                    data["power"] = round(record["voltage"] * record["current"] * 1000) / 1000
                    if record["current"] <= 0 and record["current"] >= 0:
                        data["resistance"] = 9999.9
                    else:
                        data["resistance"] = round(record["voltage"] / record["current"] * 10) / 10
                        if data["resistance"] > 9999.9:
                            data["resistance"] = 9999.9

                    if previous_timestamp is not None:
                        delta = (timestamp - previous_timestamp) / 3600
                        accumulated_current += (data["current"] * 1000) * delta
                        accumulated_power += (data["power"] * 1000) * delta

                self.storage.store_measurement(data)

                previous_timestamp = timestamp

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            message = "Failed to connect:"
            exception = traceback.format_exc()
            self.storage.log(exception)
            message += "\n%s" % exception
            messages.append(message)
        finally:
            interface.disconnect()
            self.import_in_progress = False

        return messages

    def render_csv_import(self):
        self.init()
        self.fill_config_from_parameters()

        messages = []

        session_name = "My CSV import"
        version = self.config.read("version")
        if "do" in request.form:
            session_name = request.form.get("session_name")
            if not session_name:
                messages.append("Please provide session name")

            version = request.form.get("version")
            if not version:
                messages.append("Please provide version")

            uploaded_file = request.files.get("file")
            if not uploaded_file or uploaded_file.filename == "":
                messages.append("Please select a CSV file")
            else:
                extension = pathlib.Path(uploaded_file.filename).suffix[1:].lower()
                if extension != "csv":
                    messages.append("Selected file '%s' is not a CSV file" % uploaded_file.filename)

            if len(messages) == 0:
                messages.extend(self.do_csv_import(session_name, version, uploaded_file))
                if len(messages) == 0:
                    return redirect(url_for("index.graph"))

        return render_template(
            "csv-import.html",
            messages=messages,
            session_name=session_name,
            import_version=version,
            page="data"
        )

    def do_csv_import(self, session_name, version, uploaded_file):
        temp_dir = os.path.join(get_data_path(), "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        filename = secure_filename(uploaded_file.filename)
        file_path = os.path.join(temp_dir, filename)
        uploaded_file.save(file_path)

        messages = []
        if self.import_in_progress:
            messages.append("Import is already running")
            return messages
        self.import_in_progress = True

        self.storage.fetch_status()
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                csv_reader = csv.reader(file, delimiter=",")

                header_expected = True
                mapping: dict = {}
                format = Format(version)
                session_id = None
                row_number = 0
                chunk = []
                for row in csv_reader:
                    row_number += 1
                    if header_expected:
                        header_expected = False
                        index = 0
                        for name in row:
                            field = format.field_name_reverse(name)
                            if field is not None:
                                mapping[field] = index
                            index += 1

                        if "time" not in mapping:
                            messages.append(
                                "Invalid CSV layout: time column not found, make sure your column names are correct"
                            )
                            return messages
                    else:
                        if session_id is None:
                            session_id = self.storage.create_session(session_name, version)

                        time_index = mapping["time"]
                        try:
                            time = pendulum.from_format(row[time_index], format.time_format)
                        except ValueError:
                            messages.append("Warning: unable to parse time: %s, skipping row: %s" % (
                                row[time_index], row_number
                            ))
                            continue

                        data = {
                            "timestamp": time.timestamp(),
                            "voltage": 0,
                            "current": 0,
                            "power": 0,
                            "temperature": 0,
                            "data_plus": 0,
                            "data_minus": 0,
                            "mode_id": 0,
                            "mode_name": None,
                            "accumulated_current": 0,
                            "accumulated_power": 0,
                            "accumulated_time": 0,
                            "resistance": 0,
                            "session_id": session_id,
                        }
                        for field in data.keys():
                            if field in mapping:
                                column_index = mapping[field]
                                data[field] = float(row[column_index])

                        chunk.append(data)

                        if len(chunk) >= 1000:
                            self.storage.store_measurements(chunk)
                            chunk = []

                if len(chunk):
                    self.storage.store_measurements(chunk)

            os.remove(file_path)
        finally:
            self.import_in_progress = False

        return messages

    def url_for(self, endpoint, **values):
        if endpoint == "static":
            filename = values.get("filename", None)
            if filename:
                file_path = static_path + "/" + filename
                values["v"] = int(os.stat(file_path).st_mtime)
        return url_for(endpoint, **values)

    def format_date(self, timestamp):
        date = pendulum.from_timestamp(timestamp)
        return date.in_timezone("local").format("YYYY-MM-DD HH:mm:ss")

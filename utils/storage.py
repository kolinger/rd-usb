from contextlib import closing
import logging
import os
import shutil
import sqlite3
from time import time

import pendulum

from utils.config import data_path
from utils.converter import Converter


class Storage:
    sqlite = None
    schema_version = 2

    def __init__(self):
        self.parameters = {
            "database": data_path + "/data.db",
            "isolation_level": None,
        }
        self.converter = Converter()

    def connect(self):
        connection = sqlite3.connect(**self.parameters)
        connection.row_factory = self.row_factory
        return connection

    def row_factory(self, cursor, row):
        dictionary = {}
        for index, column in enumerate(cursor.description):
            dictionary[column[0]] = row[index]
        return dictionary

    def init(self):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            tables = []
            for row in cursor.fetchall():
                tables.append(row["name"])

            schema_version = self.schema_version
            if "version" not in tables:
                cursor.execute("CREATE TABLE version (version INTEGER)")
                cursor.execute("INSERT INTO version VALUES (%s)" % self.schema_version)
            else:
                schema_version = int(cursor.execute("SELECT version FROM version").fetchone()["version"])

            if "status" not in tables:
                cursor.execute("CREATE TABLE status (status TEXT)")
                cursor.execute("INSERT INTO status VALUES ('disconnected')")

            if "logs" not in tables:
                cursor.execute((
                    "CREATE TABLE logs ("
                    "id INTEGER PRIMARY KEY,"
                    "message TEXT"
                    ")"
                ))

            if "measurements" not in tables:
                cursor.execute((
                    "CREATE TABLE measurements ("
                    "id INTEGER PRIMARY KEY,"
                    "name TEXT,"
                    "timestamp INTEGER,"
                    "voltage REAL,"
                    "current REAL,"
                    "power REAL,"
                    "temperature REAL,"
                    "data_plus REAL,"
                    "data_minus REAL,"
                    "mode_id INTEGER,"
                    "mode_name TEXT,"
                    "accumulated_current INTEGER,"
                    "accumulated_power INTEGER,"
                    "accumulated_time INTEGER,"
                    "resistance REAL,"
                    "session_id INTEGER"
                    ")"
                ))

            if "sessions" not in tables:
                cursor.execute((
                    "CREATE TABLE sessions ("
                    "id INTEGER PRIMARY KEY,"
                    "version TEXT,"
                    "name TEXT,"
                    "timestamp INTEGER"
                    ")"
                ))

            if schema_version == 1:
                logging.info("migrating database to new version, this may take a while...")

                self.backup()

                cursor.execute((
                    "ALTER TABLE measurements ADD session_id INTEGER"
                ))

                cursor.execute("DELETE FROM measurements WHERE name = '' OR name IS NULL")

                query = cursor.execute(
                    "SELECT name, MIN(timestamp) AS timestamp FROM measurements WHERE session_id IS NULL GROUP BY name ORDER BY MIN(id)")
                rows = query.fetchall()
                for row in rows:
                    session_name = row["name"]
                    cursor.execute("INSERT INTO sessions (name, timestamp) VALUES (:name, :timestamp)", (
                        session_name, row["timestamp"]
                    ))
                    session_id = cursor.lastrowid
                    cursor.execute("UPDATE measurements SET session_id = :session_id WHERE name = :name", (
                        session_id, session_name
                    ))

                cursor.execute("UPDATE version SET version = 2")

    def store_measurement(self, data):
        if data is None:
            return

        columns = []
        placeholders = []
        values = []
        for name, value in data.items():
            columns.append(name)
            placeholders.append(":" + name)
            values.append(value)

        columns = ", ".join(columns)
        placeholders = ", ".join(placeholders)
        values = tuple(values)

        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("INSERT INTO measurements (" + columns + ") VALUES (" + placeholders + ")", values)

    def destroy_measurements(self, session):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("DELETE FROM measurements WHERE session_id = ?", (session,))
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session,))

    def fetch_sessions(self):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            return cursor.execute("SELECT * FROM sessions ORDER BY timestamp DESC").fetchall()

    def fetch_measurements_count(self, session):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT COUNT(id) AS count FROM measurements WHERE session_id = ?", (session,))
            return int(cursor.fetchone()["count"])

    def fetch_measurements(self, session, limit=None, offset=None):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            sql = "SELECT * FROM measurements WHERE session_id = ? ORDER BY timestamp ASC"
            if limit is None or offset is None:
                cursor.execute(sql, (session,))
            else:
                cursor.execute(sql + " LIMIT ?, ?", (session, offset, limit))
            items = cursor.fetchall()

        for index, item in enumerate(items):
            items[index] = self.converter.convert(item)

        return items

    def fetch_last_measurement_by_name(self, name):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT * FROM measurements WHERE name = ? ORDER BY timestamp DESC LIMIT 1", (name,))
            return cursor.fetchone()

    def fetch_last_measurement(self):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT * FROM measurements ORDER BY timestamp DESC LIMIT 1")
            return cursor.fetchone()

    def get_selected_session(self, selected):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            if selected == "":
                session = cursor.execute("SELECT * FROM sessions ORDER BY timestamp DESC LIMIT 1").fetchone()
            else:
                session = cursor.execute("SELECT * FROM sessions WHERE id = ?", (selected,)).fetchone()

        return session

    def log(self, message):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("INSERT INTO logs (message) VALUES (?)", (message,))

    def fetch_log(self):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT message FROM logs")

            log = ""
            for row in cursor.fetchall():
                log += row["message"]

        return log

    def clear_log(self):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("DELETE FROM logs WHERE id NOT IN (SELECT id FROM logs ORDER BY id DESC LIMIT 250)")

    def update_status(self, status):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("UPDATE status SET status = ?", (status,))

    def fetch_status(self):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT status FROM status")
            return cursor.fetchone()["status"]

    def create_session(self, name, version):
        with closing(self.connect()) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("INSERT INTO sessions (name, version, timestamp) VALUES (?, ?, ?)", (name, version, time()))
            return cursor.lastrowid

    def backup(self):
        path = self.parameters["database"]
        backup_path = "%s.backup-%s" % (path, pendulum.now().format("YYYY-MM-DD_HH-mm-ss"))
        if os.path.exists(path):
            shutil.copy(path, backup_path)

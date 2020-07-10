import sqlite3

from utils.config import data_path


class Storage:
    sqlite = None

    def __init__(self):
        self.parameters = {
            "database": data_path + "/data.db",
            "isolation_level": None,
        }

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
        with self.connect() as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            tables = []
            for row in cursor.fetchall():
                tables.append(row["name"])

            if "version" not in tables:
                cursor.execute("CREATE TABLE version (version INTEGER)")
                cursor.execute("INSERT INTO version VALUES (1)")

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
                    "accumulated_power integer,"
                    "accumulated_time INTEGER,"
                    "resistance REAL"
                    ")"
                ))

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

        with sqlite3.connect(**self.parameters) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("INSERT INTO measurements (" + columns + ") VALUES (" + placeholders + ")", values)

    def destroy_measurements(self, name):
        with sqlite3.connect(**self.parameters) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("DELETE FROM measurements WHERE name = ?", (name,))

    def fetch_measurement_names(self):
        with self.connect() as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT name FROM measurements GROUP BY name ORDER BY timestamp DESC")

            names = []
            for row in cursor.fetchall():
                names.append(row["name"])

        return names

    def fetch_measurements_count(self, name):
        if not name:
            return 0

        with self.connect() as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT COUNT(id) AS count FROM measurements WHERE name = ?", (name,))
            return int(cursor.fetchone()["count"])

    def fetch_measurements(self, name, limit=None, offset=None):
        if not name:
            return []

        with self.connect() as sqlite:
            cursor = sqlite.cursor()
            sql = "SELECT * FROM measurements WHERE name = ? ORDER BY timestamp ASC"
            if limit is None or offset is None:
                cursor.execute(sql, (name,))
            else:
                cursor.execute(sql + " LIMIT ?, ?", (name, offset, limit))
            return cursor.fetchall()

    def fetch_last_measurement_by_name(self, name):
        with self.connect() as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT * FROM measurements WHERE name = ? ORDER BY timestamp DESC LIMIT 1", (name,))
            return cursor.fetchone()

    def fetch_last_measurement(self):
        with self.connect() as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT * FROM measurements ORDER BY timestamp DESC LIMIT 1")
            return cursor.fetchone()

    def translate_selected_name(self, selected):
        if selected == "":
            last = self.fetch_last_measurement()
            if last:
                return last["name"]

        return selected

    def log(self, message):
        with sqlite3.connect(**self.parameters) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("INSERT INTO logs (message) VALUES (?)", (message,))

    def fetch_log(self):
        with self.connect() as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT message FROM logs")

            log = ""
            for row in cursor.fetchall():
                log += row["message"]

        return log

    def clear_log(self):
        with sqlite3.connect(**self.parameters) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("DELETE FROM logs WHERE id NOT IN (SELECT id FROM logs ORDER BY id DESC LIMIT 250)")

    def update_status(self, status):
        with sqlite3.connect(**self.parameters) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("UPDATE status SET status = ?", (status,))

    def fetch_status(self):
        with sqlite3.connect(**self.parameters) as sqlite:
            cursor = sqlite.cursor()
            cursor.execute("SELECT status FROM status")
            return cursor.fetchone()[0]

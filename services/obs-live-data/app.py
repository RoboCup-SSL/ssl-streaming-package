# live/app.py
"""Flask server: serves per-field now/next/countdown JSON for OBS obs-urlsource.

Run: PORT=8000 python live/app.py   (binds 0.0.0.0 so other PCs reach it over LAN)
"""
import json
import os
from datetime import datetime

from flask import Flask, jsonify

from schedule_logic import resolve

DEFAULT_DATA = os.path.join(os.path.dirname(__file__), "data", "schedule.json")


def create_app(data_path=DEFAULT_DATA):
    app = Flask(__name__)
    cache = {"mtime": None, "data": None}

    def load_data():
        """Re-read schedule.json when its mtime changes. If a re-read fails
        (missing file or mid-edit invalid JSON), keep serving the last good
        data and retry on the next request, so overlays never blank mid-stream."""
        try:
            mtime = os.path.getmtime(data_path)
        except OSError:
            if cache["data"] is not None:
                return cache["data"]
            raise
        if cache["mtime"] != mtime:
            try:
                with open(data_path, encoding="utf-8") as fh:
                    new_data = json.load(fh)
            except (OSError, json.JSONDecodeError):
                if cache["data"] is not None:
                    return cache["data"]  # keep last good; mtime NOT updated -> retry next time
                raise
            cache["data"] = new_data
            cache["mtime"] = mtime
        return cache["data"]

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/field/<field>")
    def field(field):
        try:
            return jsonify(resolve(load_data(), field, datetime.now()))
        except ValueError as exc:
            msg = str(exc)
            code = 404 if msg.startswith("unknown field") else 422
            return jsonify(error=msg), code

    return app


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host=host, port=port, threaded=True)

#!/usr/bin/env python3

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DEVICES_FILE = Path("/mock/devices.json")


class NetBoxMockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/healthz":
            self.send_json({"status": "ok"})
            return

        if parsed_url.path == "/api/dcim/devices/":
            self.send_devices(parsed_url.query)
            return

        self.send_json({"detail": "Not found."}, status=404)

    def send_devices(self, query_string):
        with DEVICES_FILE.open(encoding="utf-8") as devices_file:
            devices = json.load(devices_file)

        query = parse_qs(query_string)

        # KTranslate requests active devices. Mimic enough NetBox behavior
        # to make Molecule fail if an unexpected filter is introduced.
        requested_status = query.get("status", [])

        if requested_status and "active" not in requested_status:
            devices = []

        response = {
            "count": len(devices),
            "next": None,
            "previous": None,
            "results": devices,
        }

        self.send_json(response)

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, message_format, *args):
        print(
            "%s - %s"
            % (
                self.address_string(),
                message_format % args,
            ),
            flush=True,
        )


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8000), NetBoxMockHandler)
    print("NetBox mock listening on 0.0.0.0:8000", flush=True)
    server.serve_forever()
#!/usr/bin/env python3
"""Small ktranslate stand-in used only by Molecule.

It understands the flags used by the role, validates that the SNMP YAML exists,
and exposes a Prometheus-compatible /metrics endpoint. This allows the role's
systemd, configuration, health validation and idempotence paths to be tested
without downloading the real release or requiring reachable SNMP devices.
"""

from __future__ import annotations

import argparse
import http.server
import pathlib
import socketserver
import sys
import yaml


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        body = (
            "# HELP ktranslate_mock_up Molecule mock collector health.\n"
            "# TYPE ktranslate_mock_up gauge\n"
            "ktranslate_mock_up 1\n"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-snmp", required=True)
    parser.add_argument("-prom_listen", default="0.0.0.0:8082")
    parser.add_argument("-listen")
    parser.add_argument("-sinks")
    parser.add_argument("-format")
    parser.add_argument("-service_name")
    parser.add_argument("-log_level")
    args, _unknown = parser.parse_known_args()

    config_path = pathlib.Path(args.snmp)
    if not config_path.is_file():
        print(f"missing config: {config_path}", file=sys.stderr)
        return 2
    data = yaml.safe_load(config_path.read_text())
    if not isinstance(data, dict) or "global" not in data or "devices" not in data:
        print("invalid mock SNMP configuration", file=sys.stderr)
        return 3

    host, port_text = args.prom_listen.rsplit(":", 1)
    host = host or "0.0.0.0"
    with socketserver.TCPServer((host, int(port_text)), Handler) as server:
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Control page + UDP bridge, both running on your computer.

The browser only ever talks to this server (same machine, negligible
latency, so plain HTTP per button press is fine here - the reason
robot-car-own-server avoids that is the ESP32 being resource-constrained,
which doesn't apply to your computer). This server turns each request into
one UDP packet sent to the robot. Video is NOT proxied through here - the
page loads it directly from the robot's own MJPEG endpoint (see
robot-car-shared-wifi.ino).

Usage: python3 server/app.py
Reads ROBOT_IP (and optionally PORT) from the environment or a local .env
file (see .env.example) - if ROBOT_IP is unset, discovers the robot with
a UDP broadcast, using the same PING/PONG the firmware already replies to.
"""
import json
import os
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

WEB_DIR = Path(__file__).resolve().parent / "web"
STATIC_FILES = {
    "/": ("index.html", "text/html"),
    "/index.html": ("index.html", "text/html"),
    "/app.js": ("app.js", "application/javascript"),
}
UDP_PORT = 4210
HTTP_PORT = int(os.environ.get("PORT", 8000))


def load_dotenv(path=".env"):
    p = Path(path)
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def discover_robot_ip():
    print("ROBOT_IP not set, broadcasting for the robot...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(2)
    try:
        sock.sendto(b"PING", ("255.255.255.255", UDP_PORT))
        _, addr = sock.recvfrom(16)
        return addr[0]
    except socket.timeout:
        return None
    finally:
        sock.close()


class Handler(BaseHTTPRequestHandler):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    robot_ip = None

    def log_message(self, format, *args):
        pass  # this fires on every keypress - keep the terminal quiet

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/cmd":
            self.handle_cmd()
        elif path == "/config":
            self.send_json({"robotIp": self.robot_ip})
        else:
            self.serve_static(path)

    def handle_cmd(self):
        params = dict(parse_qsl(urlsplit(self.path).query))
        cmd = params.get("c", "")
        if cmd:
            self.udp_sock.sendto(cmd.encode(), (self.robot_ip, UDP_PORT))
        self.send_response(204)
        self.end_headers()

    def send_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, path):
        entry = STATIC_FILES.get(path)
        if not entry:
            self.send_response(404)
            self.end_headers()
            return
        filename, content_type = entry
        body = (WEB_DIR / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    load_dotenv()
    robot_ip = os.environ.get("ROBOT_IP") or discover_robot_ip()
    if not robot_ip:
        sys.exit("Could not find the robot. Set ROBOT_IP in .env (see .env.example).")

    Handler.robot_ip = robot_ip
    print(f"Robot at {robot_ip}")
    print(f"Open http://localhost:{HTTP_PORT}")
    ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()

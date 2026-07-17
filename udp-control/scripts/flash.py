#!/usr/bin/env python3
"""Compile the sketch and flash it onto the ESP32-CAM.

Usage: python3 scripts/flash.py
Requires arduino-cli on PATH (https://arduino.github.io/arduino-cli/) with
the esp32 core installed - the script will offer to install it if missing.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
FQBN = "esp32:esp32:esp32cam"  # AI-Thinker ESP32-CAM - keeps PSRAM always on
UPLOAD_SPEEDS = [115200, 230400, 460800, 921600]
DEFAULT_SPEED = 115200  # this board's cheap USB-UART adapter is unreliable above this
IGNORED_PORT_HINTS = ("bluetooth", "debug-console")


def run(cmd, **kw):
    cmd = [str(c) for c in cmd]
    print("$", " ".join(cmd))
    return subprocess.run(cmd, **kw)


def require_arduino_cli():
    if shutil.which("arduino-cli") is None:
        sys.exit(
            "arduino-cli not found on PATH. Install it with:\n"
            "  curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh "
            "| BINDIR=/usr/local/bin sh"
        )


def require_secrets():
    if not (PROJECT_DIR / "secrets.h").is_file():
        sys.exit(
            "secrets.h not found (it's gitignored, so a fresh clone won't have it).\n"
            "  cp secrets.h.example secrets.h\n"
            "then fill in your WiFi network and run this again."
        )


def ensure_core_installed():
    out = subprocess.run(["arduino-cli", "core", "list", "--format", "json"],
                          capture_output=True, text=True, check=True)
    cores = {c["id"] for c in json.loads(out.stdout or "{}").get("platforms", [])}
    if "esp32:esp32" in cores:
        return
    if input("esp32 core not installed. Install it now (~250MB download)? [y/N] ").strip().lower() != "y":
        sys.exit("Aborted: esp32 core is required.")
    run(["arduino-cli", "core", "install", "esp32:esp32"], check=True)


def list_ports():
    out = subprocess.run(["arduino-cli", "board", "list", "--format", "json"],
                          capture_output=True, text=True, check=True)
    ports = json.loads(out.stdout or "{}").get("detected_ports", [])
    addresses = [p["port"]["address"] for p in ports if p["port"].get("protocol") == "serial"]
    return [a for a in addresses if not any(h in a.lower() for h in IGNORED_PORT_HINTS)]


def prompt_choice(items, prompt, default=None):
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            return items[int(raw) - 1]
        except (ValueError, IndexError):
            print(f"Enter a number from 1 to {len(items)}.")


def choose_port():
    ports = list_ports()
    if not ports:
        sys.exit("No serial ports found. Is the board plugged in?")
    if len(ports) == 1:
        print(f"Using port {ports[0]}")
        return ports[0]
    print("Multiple serial ports found:")
    for i, p in enumerate(ports, 1):
        print(f"  {i}) {p}")
    return prompt_choice(ports, f"Pick a port [1-{len(ports)}]: ")


def choose_speed():
    print("Upload speed:")
    for i, s in enumerate(UPLOAD_SPEEDS, 1):
        marker = " (default)" if s == DEFAULT_SPEED else ""
        print(f"  {i}) {s}{marker}")
    return prompt_choice(
        UPLOAD_SPEEDS,
        f"Pick a speed [1-{len(UPLOAD_SPEEDS)}, Enter for {DEFAULT_SPEED}]: ",
        default=DEFAULT_SPEED,
    )


def main():
    require_arduino_cli()
    require_secrets()
    ensure_core_installed()

    print("== compiling ==")
    run(["arduino-cli", "compile", "--fqbn", FQBN, PROJECT_DIR], check=True)

    port = choose_port()
    speed = choose_speed()

    print(f"== uploading @ {speed} baud ==")
    run([
        "arduino-cli", "upload",
        "--fqbn", FQBN,
        "-p", port,
        "--upload-property", f"upload.speed={speed}",
        PROJECT_DIR,
    ], check=True)

    print("Done. Open Serial Monitor (115200 baud) to see the assigned IP.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(f"{e.args[0]!r} failed with exit code {e.returncode}")
    except KeyboardInterrupt:
        sys.exit(1)

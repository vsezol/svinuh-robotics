"""Shared arduino-cli plumbing: core checks, port/speed selection, compile+upload.

Used by cli.py - not project-specific, this is the "one flashing pipeline"
every project in this repo shares.
"""
import json
import shutil
import subprocess
import sys

UPLOAD_SPEEDS = [115200, 230400, 460800, 921600]
DEFAULT_SPEED = 115200  # these boards' cheap USB-UART adapters are unreliable above this
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


def ensure_core_installed(core="esp32:esp32"):
    out = subprocess.run(["arduino-cli", "core", "list", "--format", "json"],
                          capture_output=True, text=True, check=True)
    cores = {c["id"] for c in json.loads(out.stdout or "{}").get("platforms", [])}
    if core in cores:
        return
    if input(f"{core} core not installed. Install it now (~250MB download)? [y/N] ").strip().lower() != "y":
        sys.exit(f"Aborted: {core} core is required.")
    run(["arduino-cli", "core", "install", core], check=True)


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


def flash(project_dir, fqbn, prebuild=None, secrets_file=None):
    require_arduino_cli()
    ensure_core_installed()

    if secrets_file and not (project_dir / secrets_file).is_file():
        sys.exit(
            f"{project_dir.name}/{secrets_file} not found (gitignored, so a fresh "
            "clone won't have it).\n"
            f"  cp {project_dir.name}/{secrets_file}.example {project_dir.name}/{secrets_file}\n"
            "then fill it in and run this again."
        )

    if prebuild:
        print("== running prebuild step ==")
        run(prebuild, check=True)

    print("== compiling ==")
    run(["arduino-cli", "compile", "--fqbn", fqbn, project_dir], check=True)

    port = choose_port()
    speed = choose_speed()

    print(f"== uploading @ {speed} baud ==")
    run([
        "arduino-cli", "upload",
        "--fqbn", fqbn,
        "-p", port,
        "--upload-property", f"upload.speed={speed}",
        project_dir,
    ], check=True)

    print("Done.")

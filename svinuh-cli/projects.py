"""Registry of flashable projects in this repo. Add a new one here and both
`./svinuh list` and `./svinuh flash <name>` pick it up - nothing else to wire up.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _project(name, desc, secrets_file=None, prebuild_script=None):
    project_dir = REPO_ROOT / name
    prebuild = [sys.executable, str(project_dir / prebuild_script)] if prebuild_script else None
    return {
        "dir": project_dir,
        "desc": desc,
        "fqbn": "esp32:esp32:esp32cam",  # AI-Thinker ESP32-CAM - every project here runs on it
        "prebuild": prebuild,
        "secrets_file": secrets_file,
    }


PROJECTS = {
    "web-cam-manual": _project(
        "web-cam-manual",
        "ESP32 access point + web UI (WebSocket control, MJPEG camera)",
        prebuild_script="scripts/build_web.py",
    ),
    "udp-control": _project(
        "udp-control",
        "ESP32 joins your WiFi, control page runs on your computer (UDP + MJPEG)",
        secrets_file="secrets.h",
    ),
}

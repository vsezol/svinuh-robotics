"""Loads the project registry from svinuh.yml at the repo root. Add an
entry there for a new project - nothing to change in this file."""
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit(
        "PyYAML is required to read svinuh.yml. Install it with:\n"
        "  pip3 install pyyaml"
    )

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_projects():
    config = yaml.safe_load((REPO_ROOT / "svinuh.yml").read_text())
    default_fqbn = config.get("fqbn")

    projects = {}
    for entry in config["projects"]:
        name = entry["name"]
        project_dir = REPO_ROOT / name
        prebuild_script = entry.get("prebuild_script")
        projects[name] = {
            "dir": project_dir,
            "desc": entry.get("desc", ""),
            "fqbn": entry.get("fqbn", default_fqbn),
            "prebuild": [sys.executable, str(project_dir / prebuild_script)] if prebuild_script else None,
            "secrets_file": entry.get("secrets_file"),
        }
    return projects


PROJECTS = load_projects()

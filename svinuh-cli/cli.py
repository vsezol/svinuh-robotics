"""svinuh - flash any project in this repo from one place. Entry point is
the ./svinuh executable at the repo root; this module is imported by it."""
import sys

from flasher import flash, prompt_choice
from projects import PROJECTS


def usage():
    print("Usage: svinuh flash [project]")
    print("       svinuh list")
    print()
    cmd_list()


def cmd_list():
    for name, cfg in PROJECTS.items():
        print(f"  {name:<16} {cfg['desc']}")


def cmd_flash(args):
    names = list(PROJECTS)
    if args:
        name = args[0]
    else:
        for i, n in enumerate(names, 1):
            print(f"  {i}) {n} - {PROJECTS[n]['desc']}")
        name = prompt_choice(names, f"Pick a project [1-{len(names)}]: ")

    project = PROJECTS.get(name)
    if not project:
        sys.exit(f"Unknown project '{name}'. Run './svinuh list' to see available ones.")

    flash(
        project["dir"],
        project["fqbn"],
        prebuild=project["prebuild"],
        secrets_file=project["secrets_file"],
    )


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        usage()
        return 0

    command, *rest = argv
    if command == "list":
        cmd_list()
    elif command == "flash":
        cmd_flash(rest)
    else:
        usage()
        return 1
    return 0

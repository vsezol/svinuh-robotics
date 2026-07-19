#!/bin/sh
# One-command launcher. First run creates a venv and installs deps
# (ultralytics + opencv, takes a few minutes); after that it just starts.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
exec .venv/bin/python brain.py "$@"

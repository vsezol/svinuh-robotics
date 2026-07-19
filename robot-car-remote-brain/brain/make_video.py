#!/usr/bin/env python3
"""Assemble a frames folder recorded by brain.py --record into an mp4.

Usage: .venv/bin/python make_video.py recordings/<timestamp> [fps]
Writes recordings/<timestamp>.mp4 next to the folder. Default 10 fps -
roughly what the brain processes; pass a real fps if you counted one.
"""
import sys
from pathlib import Path

import cv2


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip())
    folder = Path(sys.argv[1])
    fps = float(sys.argv[2]) if len(sys.argv) > 2 else 10
    frames = sorted(folder.glob("*.jpg"))
    if not frames:
        sys.exit(f"No .jpg frames in {folder}")

    h, w = cv2.imread(str(frames[0])).shape[:2]
    out_path = folder.with_suffix(".mp4")
    out = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for f in frames:
        out.write(cv2.imread(str(f)))
    out.release()
    print(f"{out_path} ({len(frames)} frames @ {fps:g} fps)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""The brain half of robot-car-remote-brain - all thinking happens here, on your
computer. The robot (../robot/) is a dumb layer that streams camera
frames and obeys single-letter UDP commands; this script closes the loop:
find the robot, watch its camera, run YOLO person detection, steer.

Behavior: turn to keep the person horizontally centered, drive
forward/backward to keep their bounding box at the target height
(size-in-frame replaces distance, so people of any height work). When
nobody is in frame the robot searches: a short spin, then a pause to
look, repeat - slow enough that YOLO can't miss someone sweeping past.

Usage:
    pip install -r requirements.txt
    python3 brain.py [robot-ip] [--record]   # ip optional, discovers via UDP broadcast

The UI is a local page (NiceGUI) that opens in your browser: camera on
the left, controls on the right - a Manual switch, a Follow toggle
(person or dog - the same COCO model knows both), target-size / speed
sliders and live status. In manual mode drive with WASD or the arrow
keys (works in any keyboard layout, proper press/release), Space =
stop. --record dumps every annotated frame to recordings/<ts>/
(make_video.py turns a folder into an mp4).
"""
import base64
import os
import socket
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from nicegui import app, ui
from ultralytics import YOLO

UDP_PORT = 4210    # firmware listens here (commands + PING/PONG discovery)
STREAM_PORT = 81   # firmware's MJPEG endpoint
UI_PORT = 8080     # the control page, http://localhost:8080

# Tuning. Sizes and offsets are fractions of the frame, so they work at
# any camera resolution. Target height and speed are just the slider
# defaults - adjust them live in the UI.
TARGET_HEIGHT = 0.6    # person bbox height to hold, as fraction of frame height
HEIGHT_DEADZONE = 0.1  # don't drive while height is within target +/- this
CENTER_DEADZONE = 0.12 # don't turn while person is within +/- this of frame center
MIN_CONFIDENCE = 0.5
SPEED = 200            # drive speed slider default (below ~140 the wheels may not move)
LOST_GRACE = 1.0       # seconds without a person before search mode kicks in
SPIN_T, LOOK_T = 0.2, 0.6  # search cycle: spin briefly, then stand still and look

# Physical key codes (layout-independent) -> commands.
KEY_MAP = {"KeyW": "F", "KeyS": "B", "KeyA": "L", "KeyD": "R",
           "ArrowUp": "F", "ArrowDown": "B", "ArrowLeft": "L", "ArrowRight": "R"}

# What to follow. Same yolov8n model knows both - these are COCO class ids.
TRACK_CLASSES = {"person": 0, "dog": 16}

# Everything the control thread and the UI share. Plain dict + GIL is
# plenty here - single writer per key, readers tolerate a stale frame.
state = {
    "manual": False, "target": TARGET_HEIGHT * 100, "speed": SPEED,
    "track": "person",   # or "dog" - what the robot follows
    "manual_cmd": "S",   # what WASD currently holds down
    "cmd": "S", "people": 0, "offset": None, "height": None,
    "searching": False, "connected": False,
    "jpg": None,         # newest annotated frame as a data-url
    "quit": False,
}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
robot_ip = None
rec_dir = None
frame_no = 0


def discover_robot_ip():
    print("Broadcasting for the robot...")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(2)
    try:
        s.sendto(b"PING", ("255.255.255.255", UDP_PORT))
        _, addr = s.recvfrom(16)
        return addr[0]
    except socket.timeout:
        return None
    finally:
        s.close()


def mjpeg_frames(ip):
    """Yield the NEWEST frame of the robot's MJPEG stream, never a stale
    one. If YOLO is slower than the camera, unread frames pile up in the
    OS socket buffer and the picture ends up seconds behind reality - so
    each cycle drains everything the robot has sent so far (non-blocking
    recv until empty) and decodes only the last complete JPEG in it,
    dropping the older ones. Plain socket instead of urllib/VideoCapture
    because neither lets us drain like this (and VideoCapture can't open
    the ESP32's multipart stream at all)."""
    s = socket.create_connection((ip, STREAM_PORT), timeout=5)
    s.sendall(f"GET /stream HTTP/1.1\r\nHost: {ip}\r\n\r\n".encode())
    buf = b""
    try:
        while True:
            s.settimeout(5)
            chunk = s.recv(65536)  # wait for fresh data...
            if not chunk:
                return  # robot closed the stream
            buf += chunk
            s.settimeout(0)  # ...then grab whatever else has already arrived
            try:
                while True:
                    chunk = s.recv(65536)
                    if not chunk:
                        return
                    buf += chunk
            except BlockingIOError:
                pass
            # newest complete jpeg = last end marker and the start before it
            end = buf.rfind(b"\xff\xd9")
            start = buf.rfind(b"\xff\xd8", 0, end) if end != -1 else -1
            if start == -1:
                continue  # no complete frame yet, keep reading
            jpg, buf = buf[start:end + 2], buf[end + 2:]
            frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                yield frame
    finally:
        s.close()


def decide(frame_w, frame_h, person_boxes, target):
    """Person boxes -> one command letter. Turning wins over driving:
    face the person first, then fix the distance."""
    if not person_boxes:
        return "S", None
    box = max(person_boxes, key=lambda b: b[3] - b[1])  # tallest box = nearest person
    x1, y1, x2, y2 = box
    offset = (x1 + x2) / 2 / frame_w - 0.5  # -0.5 (left edge) .. +0.5 (right edge)
    height = (y2 - y1) / frame_h
    if offset < -CENTER_DEADZONE:
        cmd = "L"
    elif offset > CENTER_DEADZONE:
        cmd = "R"
    elif height < target - HEIGHT_DEADZONE:
        cmd = "F"
    elif height > target + HEIGHT_DEADZONE:
        cmd = "B"
    else:
        cmd = "S"
    return cmd, box


def draw_overlay(frame, box, recording):
    """Markings on the frame itself (also ends up in recordings):
    dead-zone lines, detection box, REC dot. Textual status lives in
    the side panel, not on the picture."""
    h, w = frame.shape[:2]
    for x in (int(w * (0.5 - CENTER_DEADZONE)), int(w * (0.5 + CENTER_DEADZONE))):
        cv2.line(frame, (x, 0), (x, h), (80, 80, 80), 1)
    if box:
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    if recording:
        cv2.circle(frame, (w - 16, 16), 6, (0, 0, 255), -1)


def send(cmd):
    sock.sendto(cmd.encode(), (robot_ip, UDP_PORT))


def control_loop():
    """Vision + steering, runs in a background thread; talks to the UI
    only through the shared `state` dict."""
    global frame_no
    model = YOLO("yolov8n.pt")  # nano model, auto-downloads (~6 MB) on first run

    last_seen = time.time()  # counts as "just seen" so startup doesn't spin instantly
    search_dir = "R"         # spin toward where the person was last seen
    manual_prev = False
    while not state["quit"]:
        try:
            for frame in mjpeg_frames(robot_ip):
                if state["quit"]:
                    break
                now = time.time()
                state["connected"] = True
                target = max(0.2, state["target"] / 100)
                manual = state["manual"]
                if manual != manual_prev:  # fresh start in either mode
                    manual_prev = manual
                    state["manual_cmd"] = "S"
                    last_seen = now

                frame = cv2.flip(frame, 1)  # raw stream is mirrored (see robot/Camera.cpp)
                h, w = frame.shape[:2]
                result = model(frame, classes=[TRACK_CLASSES[state["track"]]],
                               conf=MIN_CONFIDENCE, verbose=False)[0]
                boxes = [b.xyxy[0].tolist() for b in result.boxes]
                cmd, box = decide(w, h, boxes, target)

                searching = False
                if manual:
                    # you drive; detection keeps running just for the overlay
                    cmd = state["manual_cmd"]
                elif box:
                    last_seen = now
                    search_dir = "L" if (box[0] + box[2]) / 2 < w / 2 else "R"
                elif now - last_seen > LOST_GRACE:
                    # nobody in frame: spin a little, then hold still so
                    # YOLO gets sharp, unhurried looks - slow enough not
                    # to sweep past a person between frames
                    searching = True
                    cmd = search_dir if (now - last_seen) % (SPIN_T + LOOK_T) < SPIN_T else "S"

                send(f"V{int(state['speed'])}")  # whatever the slider says, always
                send(cmd)  # every frame - the firmware auto-stops if these stop arriving

                draw_overlay(frame, box, rec_dir is not None)
                if rec_dir:
                    frame_no += 1
                    cv2.imwrite(str(rec_dir / f"{frame_no:06d}.jpg"), frame)

                ok, jpg = cv2.imencode(".jpg", frame)
                if ok:
                    state["jpg"] = "data:image/jpeg;base64," + base64.b64encode(jpg.tobytes()).decode()
                state.update(cmd=cmd, people=len(boxes), searching=searching,
                             offset=None if not box else (box[0] + box[2]) / 2 / w - 0.5,
                             height=None if not box else (box[3] - box[1]) / h)
        except OSError:
            state["connected"] = False
            if not state["quit"]:
                time.sleep(2)  # robot rebooting / WiFi hiccup - keep retrying
    send("S")


def on_key(e):
    if e.action.repeat:
        return
    kc = str(getattr(e.key, "code", "") or e.key.name)
    if kc == "KeyM" and e.action.keydown:
        state["manual"] = not state["manual"]  # the switch follows via bind_value
        return
    if not state["manual"]:
        return
    cmd = KEY_MAP.get(kc)
    if cmd:
        if e.action.keydown:
            state["manual_cmd"] = cmd
        elif e.action.keyup and state["manual_cmd"] == cmd:
            state["manual_cmd"] = "S"
    elif kc == "Space" and e.action.keydown:
        state["manual_cmd"] = "S"


@ui.page("/")
def index_page():
    """One instance of the UI per connected browser tab; they all read
    and write the same shared `state`."""
    ui.dark_mode(True)
    ui.keyboard(on_key=on_key, ignore=[])  # WASD should work even if a slider has focus

    with ui.row().classes("p-6 gap-6 items-start flex-nowrap"):
        video = ui.interactive_image().classes(
            "w-[640px] aspect-[4/3] rounded-2xl shadow-lg bg-black shrink-0")

        with ui.card().classes("w-80 gap-2"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("robot brain").classes("text-xl font-bold")
                conn = ui.badge("connecting...", color="orange").classes("px-3 py-1")

            manual_sw = ui.switch("Manual control (M)").bind_value(state, "manual")

            hint = ui.label("WASD / arrows to drive - Space to stop").classes(
                "text-xs text-gray-500")
            hint.bind_visibility_from(manual_sw, "value")

            ui.separator()
            ui.label("Follow").classes("text-sm text-gray-400")
            ui.toggle(list(TRACK_CLASSES)).bind_value(state, "track").props("no-caps")
            ui.label("Target size, % of frame").classes("text-sm text-gray-400")
            ui.slider(min=20, max=90, value=int(TARGET_HEIGHT * 100),
                      on_change=lambda e: state.update(target=e.value)).props("label-always")
            ui.label("Speed").classes("text-sm text-gray-400")
            ui.slider(min=0, max=255, value=SPEED,
                      on_change=lambda e: state.update(speed=e.value)).props("label-always")

            ui.separator()
            info = ui.label("").classes("font-mono text-sm whitespace-pre leading-6")

            with ui.row().classes("w-full items-center justify-between mt-2"):
                if rec_dir:
                    ui.badge("REC", color="red").classes("px-3 py-1")
                else:
                    ui.element()
                ui.button("Stop & exit", color="red-9",
                          on_click=lambda: (state.update(manual=False, quit=True), app.shutdown()))

    def refresh():
        if state["jpg"]:
            video.set_source(state["jpg"])
        conn.set_text("online" if state["connected"] else "reconnecting...")
        conn.props(f"color={'green' if state['connected'] else 'orange'}")
        mode = "MANUAL" if state["manual"] else ("SEARCH" if state["searching"] else "FOLLOW")
        off = f"{state['offset']:+.2f}" if state["offset"] is not None else "-"
        hgt = f"{state['height']:.2f}" if state["height"] is not None else "-"
        info.set_text(f"mode    {mode}\n"
                      f"command {state['cmd']}\n"
                      f"{state['track'] + 's':<7} {state['people']}\n"
                      f"offset  {off}\n"
                      f"height  {hgt} / {state['target'] / 100:.2f}")

    ui.timer(1 / 15, refresh)


def main():
    global robot_ip, rec_dir
    record = "--record" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    robot_ip = args[0] if args else os.environ.get("ROBOT_IP") or discover_robot_ip()
    if not robot_ip:
        sys.exit("Robot not found. Pass its IP: python3 brain.py 192.168.1.42")
    print(f"Robot at {robot_ip}")

    if record:
        rec_dir = Path(__file__).resolve().parent / "recordings" / datetime.now().strftime("%Y%m%d-%H%M%S")
        rec_dir.mkdir(parents=True)
        print(f"Recording annotated frames to {rec_dir}")

    threading.Thread(target=control_loop, daemon=True).start()

    app.on_disconnect(lambda *_: state.update(manual_cmd="S"))  # tab closed mid-drive -> stop
    app.on_shutdown(lambda *_: state.update(quit=True))
    ui.run(title="robot brain", dark=True, port=UI_PORT, reload=False, show=True)

    # here after shutdown
    time.sleep(0.3)  # let the control thread send its final stop
    if rec_dir:
        print(f"{frame_no} frames in {rec_dir}")
        print(f"Make a video: {sys.executable} {Path(__file__).resolve().parent / 'make_video.py'} {rec_dir}")


if __name__ in {"__main__", "__mp_main__"}:
    main()

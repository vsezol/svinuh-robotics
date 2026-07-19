# robot-car-remote-brain (experiment)

Third take on the architecture: split the system into a **dumb body** and
a **big brain**.

- [`robot/`](robot) — ESP32-CAM firmware, deliberately as dumb as
  possible: join your WiFi, stream the camera (MJPEG, `:81/stream`),
  obey single-letter UDP commands (motors, LED). No UI, no logic, no
  state beyond "auto-stop if commands stop arriving". Wire protocol and
  wiring are identical to `robot-car-shared-wifi`.
- [`brain/`](brain) — one Python script on your computer. Finds the robot
  on the LAN (same UDP PING/PONG broadcast), pulls its camera stream,
  runs YOLO person detection on every frame and sends steering commands
  back.

```
robot --MJPEG frames (HTTP :81)--> brain/brain.py (YOLO on your computer)
robot <--UDP F/B/L/R/S, V, D------ brain/brain.py
```

First brain task: **follow a person**.

## How following works

There is no target distance in meters - people have different heights,
so instead the brain holds the person at a fixed *size in frame*
(`TARGET_HEIGHT`, fraction of frame height the bounding box takes up):

- person drifts left/right of center → turn `L`/`R` toward them
- bbox smaller than target (walked away) → drive `F`
- bbox bigger than target (walked closer) → drive `B`
- turning wins over driving: face the person first, then fix distance
- nobody in frame for `LOST_GRACE` seconds → search mode: a short spin
  toward where the person was last seen, a pause to look, repeat -
  slow enough that YOLO can't sweep past someone between frames

The robot naturally settles at whatever distance makes *this* person
look target-height tall. Dead zones around both targets keep it from
twitching. Target size and drive speed have sliders right on the
control page (changes apply instantly); the rest of the tuning
constants sit at the top of `brain/brain.py`.

There is also a Manual switch on the page (hotkey `M`): flip it to
drive yourself with WASD / arrow keys (any layout, proper
press/release; Space = stop) - flip it back and auto mode resumes.

A command is sent on every processed frame; the firmware auto-stops
after 400 ms of silence, so a crashed brain (or WiFi drop) can't leave
the robot driving into a wall.

## Setup

1. Robot (same as `robot-car-shared-wifi`): `cp robot/secrets.h.example
   robot/secrets.h`, fill in your WiFi, open `robot/robot.ino` in
   Arduino IDE (board AI-Thinker ESP32-CAM) and upload.
2. Brain, on a computer on the same WiFi - one command:
   ```
   ./brain/run.sh                    # or: ./brain/run.sh <robot-ip>
   ```
   First run creates a venv, installs ultralytics (YOLO) + opencv +
   nicegui and downloads the YOLOv8-nano weights (~6 MB) - takes a few
   minutes, later runs start instantly. The control page then opens in
   your browser (http://localhost:8080).

## The control page

Local page served by the brain itself (NiceGUI) - camera on the left,
controls on the right:

- live camera with the detection box and dead-zone lines drawn in
- **Manual** switch (hotkey `M`) - WASD / arrow keys to drive, Space to
  stop; works in any keyboard layout, with proper press/release
- **Follow** toggle: person or dog (same COCO model detects both, it is
  just a different class id)
- sliders for target size and drive speed, applied instantly
- live status: mode (FOLLOW / SEARCH / MANUAL), command, people count,
  horizontal offset, bbox height vs target
- online / reconnecting badge and a **Stop & exit** button

## Debugging

To keep evidence of a run, record it:

```
./brain/run.sh --record
```

Every annotated frame - exactly what the brain saw and what it decided -
is saved to `brain/recordings/<timestamp>/000001.jpg, ...` (gitignored).
Flip through them frame-by-frame, or assemble an mp4:

```
brain/.venv/bin/python brain/make_video.py brain/recordings/<timestamp>
```

Optional trailing argument = fps (default 10, roughly the brain's
processing rate). The exact copy-pasteable command is printed when the
brain exits.

# web-cam-manual

ESP32-CAM (AI-Thinker) + L298N robot: camera stream and manual drive control
over the robot's own WiFi access point (`192.168.4.1`).

## Architecture

![Runtime architecture: phone/laptop browser talks to the ESP32-CAM over WiFi AP 192.168.4.1 — HTTP GET / and /app.js load the page once, a persistent WebSocket at /ws carries movement/speed/LED commands, and HTTP GET :81/stream plus /capture serve the camera feed. Inside the ESP32, ws_handler dispatches to handle_ws_cmd(), which calls WheelAct() to drive the L298N motor driver and ledcWrite() for the onboard LED; capture_handler and stream_handler both pull frames from the OV2640 camera via esp_camera_fb_get().](docs/architecture.svg)

## Layout

- `web-cam-manual.ino`, `CameraWebServer.cpp`, `app_httpd.cpp` — firmware.
- `web/index.html`, `web/app.js` — the control page, hand-written and readable.
- `generated/web_assets.h` — **build output, not committed.** `web/` gets
  minified and gzipped at build time into a C header the firmware serves
  directly from flash; regenerate with `scripts/build_web.py`.
- `scripts/build_web.py` — regenerates `generated/web_assets.h` from `web/`.
  Flashing (build → compile → upload) is now handled from the repo root —
  see [`../svinuh-cli`](../svinuh-cli).

## Control protocol

The page talks to the robot over one persistent WebSocket (`/ws`) instead of
one HTTP request per button press — a single open socket costs a few bytes
per command instead of a full HTTP request (~300+ bytes, fresh TCP
connection each time), which is what was causing lag/dropped commands.

```
F / B / L / R / S   move forward / backward / left / right / stop
V<0-255>             set drive speed, e.g. "V220"
D<0-255>             set LED brightness, e.g. "D128"
```

`/stream` (MJPEG, port 81) and `/capture` (single JPEG) stay plain HTTP —
that's already-compressed camera bytes, nothing to gain from WebSocket there.

## Flashing

Requires [arduino-cli](https://arduino.github.io/arduino-cli/) with the
`esp32` core and board set to **AI-Thinker ESP32-CAM** (not "ESP32 Dev
Module" — that profile leaves PSRAM off by default, which starves the HTTP
server of RAM under load).

From the repo root:

```
./svinuh flash web-cam-manual
```

Builds the web assets, compiles, lets you pick a serial port (if more than
one is connected) and an upload speed, then flashes.

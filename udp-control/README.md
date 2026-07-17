# udp-control (experiment)

Alternative to `web-cam-manual`'s approach: the robot doesn't serve the
control page or run any web server for it. It joins your existing WiFi
(station mode, same network as your computer) and just listens for tiny
UDP packets. The control page is served by **your computer**
(`server/app.py`), which bridges browser button presses to UDP packets.

Video still needs *some* server, since streaming JPEG frames over raw UDP
(fragmenting datagrams, handling loss/reordering) is real work for no
benefit here - so the robot runs one small MJPEG endpoint (`/stream`,
port 81, lifted from `web-cam-manual`) and the browser loads it **directly
from the robot**, bypassing the computer entirely. The computer only ever
proxies the lightweight control commands.

```
Browser  --HTTP (localhost)-->  server/app.py  --UDP-->  robot (F/B/L/R/S, V<n>, D<n>)
Browser  --HTTP, direct-------------------------------->  robot:81/stream (MJPEG video)
```

Trade-off vs `web-cam-manual`:

- **Lighter robot firmware** - no HTTP control server, no gzip/minify
  build step, no static assets to serve. Just `WiFi.begin()` + `WiFiUDP`
  for control; the camera stream is the only HTTP surface left.
- **No standalone hotspot** - the robot needs a WiFi network with a router
  already running (unlike `web-cam-manual`'s own access point).
- **UDP has no delivery guarantee or connection state** - fine here, since
  a dropped "forward" packet just means one skipped tick, and the newest
  command always wins. The firmware auto-stops if packets stop arriving
  for 400ms, so a WiFi hiccup can't leave it driving forever.

## Setup

1. `cp secrets.h.example secrets.h` and fill in your WiFi network.
   `secrets.h` is gitignored - it never gets committed.
2. Flash it (same physical board as web-cam-manual - AI-Thinker ESP32-CAM):
   ```
   python3 scripts/flash.py
   ```
   Compiles, lets you pick a serial port (if more than one is connected)
   and an upload speed, then flashes.
3. Open Serial Monitor (115200 baud) to confirm it joined WiFi - optional,
   the server below can also find it on its own.
4. On your computer, on the same WiFi:
   ```
   python3 server/app.py
   ```
   It broadcasts for the robot automatically. If that doesn't work on your
   network, `cp .env.example .env` inside `server/` and set `ROBOT_IP`
   from the Serial Monitor output - `.env` is gitignored too.
5. Open `http://localhost:8000` - WASD or the on-screen D-pad to drive,
   sliders for speed/LED, "Start screen" for video.

## Wire protocol (computer <-> robot, over UDP)

```
F / B / L / R / S   move forward / backward / left / right / stop
V<0-255>             set drive speed
D<0-255>             set LED brightness
PING                 -> robot replies PONG (server/app.py uses this to find it)
```

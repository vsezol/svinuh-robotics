# udp-control (experiment)

Alternative to `web-cam-manual`'s approach: no web server, no static page,
no browser at all. The robot joins your existing WiFi (station mode,
same network as your computer) and just listens for tiny UDP packets.

Trade-off vs `web-cam-manual`:

- **Simpler and lighter on the robot** - no HTTP server, no gzip/minify
  build step, no static assets to serve. Just `WiFi.begin()` + `WiFiUDP`.
- **No camera video in this variant** - this is a controls-only experiment.
  Adding a video feed here would mean streaming JPEG frames over UDP
  yourself; MJPEG-over-HTTP (what `web-cam-manual` does) is the easier way
  to get video, which is why that project keeps the web server.
- **No standalone hotspot** - the robot needs a WiFi network with a router
  already running (unlike `web-cam-manual`'s own access point), and you
  need a computer to run the Python client from - no phone browser control.
- **UDP has no delivery guarantee or connection state** - fine here, since
  a dropped "forward" packet just means one skipped tick, and the newest
  command always wins. The firmware auto-stops if packets stop arriving
  for 400ms, so a WiFi hiccup can't leave it driving forever.

## Setup

1. Edit `udp-control.ino`: fill in `ssid` / `password` for your WiFi network.
2. Flash it (same board as web-cam-manual - AI-Thinker ESP32-CAM):
   ```
   arduino-cli compile --fqbn esp32:esp32:esp32cam udp-control
   arduino-cli upload --fqbn esp32:esp32:esp32cam -p <port> udp-control
   ```
3. Open Serial Monitor (115200 baud) to confirm it joined WiFi and note
   its IP - or skip that and let the client auto-discover it.
4. From a computer on the same WiFi:
   ```
   python3 client/control.py
   ```
   WASD to drive (hold to move, release to stop), +/- for speed, q to quit.

## Wire protocol

```
F / B / L / R / S   move forward / backward / left / right / stop
V<0-255>             set drive speed
D<0-255>             set LED brightness
PING                 -> robot replies PONG (client/control.py uses this to find it)
```

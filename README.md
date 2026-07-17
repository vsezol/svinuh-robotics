# svinuh-robotics

ESP32-CAM + L298N robot projects.

## Projects

- [`web-cam-manual`](web-cam-manual) — the robot runs its own WiFi access
  point and a web UI (WebSocket control, MJPEG camera stream).
- [`udp-control`](udp-control) — experiment: the robot joins your existing
  WiFi instead, and the control page runs on your computer, bridging to
  the robot over UDP. See its README for the trade-offs.

Each project's README covers flashing it (Arduino IDE — board **AI-Thinker
ESP32-CAM**).

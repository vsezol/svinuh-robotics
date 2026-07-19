# pigs-robotics

ESP32-CAM + L298N robot projects.

## Projects

- [`robot-car-own-server`](robot-car-own-server) — the robot runs its own
  WiFi access point and a web UI (WebSocket control, MJPEG camera stream).
- [`robot-car-shared-wifi`](robot-car-shared-wifi) — experiment: the robot
  joins your existing WiFi instead, and the control page runs on your
  computer, bridging to the robot over UDP. See its README for the trade-offs.
- [`robot-car-remote-brain`](robot-car-remote-brain) — experiment: the
  robot is a dumb layer (camera stream + UDP commands, no UI at all) and a
  Python "brain" on your computer runs YOLO to make it follow a person
  autonomously.

Each project's README covers flashing it (Arduino IDE — board **AI-Thinker
ESP32-CAM**).

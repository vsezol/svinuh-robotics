# svinuh-robotics

ESP32-CAM + L298N robot projects.

```
./svinuh list          # show what's here
./svinuh flash <name>   # compile and upload a project
```

## Projects

- [`web-cam-manual`](web-cam-manual) — the robot runs its own WiFi access
  point and a web UI (WebSocket control, MJPEG camera stream).
- [`udp-control`](udp-control) — experiment: the robot joins your existing
  WiFi instead, and the control page runs on your computer, bridging to
  the robot over UDP. See its README for the trade-offs.

## svinuh-cli

`svinuh-cli/` holds the shared flashing pipeline (arduino-cli checks,
port/speed selection, compile+upload) so it isn't duplicated per project.
Adding a new project means adding one entry to `svinuh-cli/projects.py` —
see that file.

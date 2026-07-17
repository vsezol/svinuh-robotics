# svinuh-robotics

ESP32-CAM + L298N robot projects.

Requires `pip3 install -r requirements.txt` once (just PyYAML, for
`svinuh.yml` below).

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

[`svinuh.yml`](svinuh.yml) is the project registry - name, description,
FQBN, any prebuild step, any gitignored secrets file it needs. Adding a
new project means adding one entry there, nothing else to wire up.

`svinuh-cli/` is the flashing pipeline that reads it: arduino-cli checks,
port/speed selection, compile+upload. `./svinuh` itself just forwards into
it - `svinuh-cli/cli.py` is where the actual command handling lives.

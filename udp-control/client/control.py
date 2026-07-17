#!/usr/bin/env python3
"""Terminal remote control for udp-control: WASD over UDP, no browser, no web server.

Usage: python3 client/control.py [robot_ip]
With no IP given, broadcasts a PING on the LAN and controls whichever
robot replies first. macOS/Linux only (uses termios for raw keyboard input).
"""
import select
import socket
import sys
import termios
import time
import tty

PORT = 4210
KEY_TO_CMD = {"w": "F", "s": "B", "a": "L", "d": "R"}
RELEASE_TIMEOUT = 0.2  # no keypress for this long -> treat the key as released
SPEED_STEP = 10


def discover(sock):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(b"PING", ("255.255.255.255", PORT))
    sock.settimeout(2)
    try:
        _, addr = sock.recvfrom(16)
        return addr[0]
    except socket.timeout:
        sys.exit("No robot replied to discovery. Pass its IP directly: control.py <ip>")


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    robot_ip = sys.argv[1] if len(sys.argv) > 1 else discover(sock)
    sock.settimeout(0)
    print(f"Controlling robot at {robot_ip}:{PORT} - WASD to move, +/- for speed, q to quit")

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)

    moving = False
    last_key_time = 0.0
    speed = 220
    try:
        while True:
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if ready:
                key = sys.stdin.read(1).lower()
                if key == "q":
                    break
                if key in KEY_TO_CMD:
                    sock.sendto(KEY_TO_CMD[key].encode(), (robot_ip, PORT))
                    moving = True
                    last_key_time = time.monotonic()
                elif key in "+-":
                    speed = max(0, min(255, speed + (SPEED_STEP if key == "+" else -SPEED_STEP)))
                    sock.sendto(f"V{speed}".encode(), (robot_ip, PORT))
                    print(f"speed={speed}")
            elif moving and time.monotonic() - last_key_time > RELEASE_TIMEOUT:
                sock.sendto(b"S", (robot_ip, PORT))
                moving = False
    finally:
        sock.sendto(b"S", (robot_ip, PORT))
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


if __name__ == "__main__":
    main()

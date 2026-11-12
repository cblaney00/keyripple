#!/usr/bin/env python3
"""Key Ripple: a soft gold ripple on a Logitech G915 every time a key is pressed.

The rest of the keyboard stays the base colour (soft Glade teal). Key presses are read
from the keyboard's own input devices (evdev). Only which key was pressed is used, to
place the ripple; nothing is stored or logged. Colours are painted through a running
OpenRGB server (Direct mode).

The keyboard has no layout map in OpenRGB, so key positions are a table below, in key
widths (x) and rows (y) on a full-size ANSI/ISO board.

Exits on any OpenRGB error; the system service restarts it (e.g. after OpenRGB restarts
when the cable is plugged in or out).
"""

import math
import os
import select
import sys
import time

import evdev
from evdev import ecodes
from openrgb import OpenRGBClient
from openrgb.utils import DeviceType, RGBColor

HOST = os.environ.get("KEYRIPPLE_HOST", "127.0.0.1")
PORT = int(os.environ.get("KEYRIPPLE_PORT", "6742"))
NAME = os.environ.get("KEYRIPPLE_DEVICE", "G915")


def hexcolor(name, default):
    v = os.environ.get(name, default).lstrip("#")
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))


# Base: 00B4A0 at 40% (what g915-teal sets). Ripple: warm firefly gold.
BASE = hexcolor("KEYRIPPLE_BASE", "00483F")
GOLD = hexcolor("KEYRIPPLE_RIPPLE", "BE7A1E")
RADIUS = float(os.environ.get("KEYRIPPLE_RADIUS", "3.0"))   # keys: "small", then "a little larger"
LIFE = float(os.environ.get("KEYRIPPLE_LIFE", "1.1"))       # seconds: "slow and gentle"
WIDTH = 0.6                                                 # ring softness, in keys
FPS = 30
DEBUG = bool(os.environ.get("KEYRIPPLE_DEBUG"))

# --- key positions (x in key widths, y in rows) -----------------------------------
POS = {}


def row(y, x0, names, step=1.0):
    for i, n in enumerate(names):
        POS[n] = (x0 + i * step, y)


POS["Escape"] = (0, 0)
row(0, 2, ["F1", "F2", "F3", "F4"])
row(0, 6.5, ["F5", "F6", "F7", "F8"])
row(0, 11, ["F9", "F10", "F11", "F12"])
row(0, 15.25, ["Print Screen", "Scroll Lock", "Pause/Break"])
POS["Brightness"] = (15.5, -1)
row(-1, 19, ["Media Previous", "Media Play/Pause", "Media Next", "Media Mute"])
row(0, -1.5, ["G1"])
row(1, -1.5, ["G2"]); row(2, -1.5, ["G3"]); row(3, -1.5, ["G4"]); row(4, -1.5, ["G5"])

row(1, 0, ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="])
POS["Backspace"] = (13.5, 1)
row(1, 15.25, ["Insert", "Home", "Page Up"])
row(1, 18.5, ["Num Lock", "Number Pad /", "Number Pad *", "Number Pad -"])

POS["Tab"] = (0.25, 2)
row(2, 1.5, list("QWERTYUIOP") + ["[", "]"])
POS["\\ (ANSI)"] = (13.75, 2)
row(2, 15.25, ["Delete", "End", "Page Down"])
row(2, 18.5, ["Number Pad 7", "Number Pad 8", "Number Pad 9"])
POS["Number Pad +"] = (21.5, 2.5)

POS["Caps Lock"] = (0.4, 3)
row(3, 1.75, list("ASDFGHJKL") + [";", "'", "#"])
POS["Enter"] = (13.4, 3)
row(3, 18.5, ["Number Pad 4", "Number Pad 5", "Number Pad 6"])

POS["Left Shift"] = (0.6, 4)
POS["\\ (ISO)"] = (1.25, 4)
row(4, 2.25, list("ZXCVBNM") + [",", ".", "/"])
POS["Right Shift"] = (13.2, 4)
POS["Up Arrow"] = (16.25, 4)
row(4, 18.5, ["Number Pad 1", "Number Pad 2", "Number Pad 3"])
POS["Number Pad Enter"] = (21.5, 4.5)

POS.update({
    "Left Control": (0.1, 5), "Left Windows": (1.4, 5), "Left Alt": (2.6, 5),
    "Space": (6.4, 5), "Right Alt": (10.1, 5), "Right Windows": (11.4, 5),
    "Menu": (12.6, 5), "Right Control": (13.9, 5),
    "Left Arrow": (15.25, 5), "Down Arrow": (16.25, 5), "Right Arrow": (17.25, 5),
    "Number Pad 0": (19, 5), "Number Pad .": (20.5, 5),
})

# --- evdev key code -> OpenRGB key name -------------------------------------------
KEYNAME = {}
for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
    KEYNAME[getattr(ecodes, "KEY_" + ch)] = ch
for i in range(1, 13):
    KEYNAME[getattr(ecodes, f"KEY_F{i}")] = f"F{i}"
for i in range(10):
    KEYNAME[getattr(ecodes, f"KEY_KP{i}")] = f"Number Pad {i}"
for code, name in {
    "ENTER": "Enter", "ESC": "Escape", "BACKSPACE": "Backspace", "TAB": "Tab",
    "SPACE": "Space", "MINUS": "-", "EQUAL": "=", "LEFTBRACE": "[", "RIGHTBRACE": "]",
    "BACKSLASH": "\\ (ANSI)", "SEMICOLON": ";", "APOSTROPHE": "'", "GRAVE": "`",
    "COMMA": ",", "DOT": ".", "SLASH": "/", "CAPSLOCK": "Caps Lock",
    "SYSRQ": "Print Screen", "SCROLLLOCK": "Scroll Lock", "PAUSE": "Pause/Break",
    "INSERT": "Insert", "HOME": "Home", "PAGEUP": "Page Up", "DELETE": "Delete",
    "END": "End", "PAGEDOWN": "Page Down", "RIGHT": "Right Arrow", "LEFT": "Left Arrow",
    "DOWN": "Down Arrow", "UP": "Up Arrow", "102ND": "\\ (ISO)", "COMPOSE": "Menu",
    "LEFTCTRL": "Left Control", "LEFTSHIFT": "Left Shift", "LEFTALT": "Left Alt",
    "LEFTMETA": "Left Windows", "RIGHTCTRL": "Right Control", "RIGHTSHIFT": "Right Shift",
    "RIGHTALT": "Right Alt", "RIGHTMETA": "Right Windows",
    "PREVIOUSSONG": "Media Previous", "PLAYPAUSE": "Media Play/Pause",
    "NEXTSONG": "Media Next", "MUTE": "Media Mute", "NUMLOCK": "Num Lock",
    "KPSLASH": "Number Pad /", "KPASTERISK": "Number Pad *", "KPMINUS": "Number Pad -",
    "KPPLUS": "Number Pad +", "KPENTER": "Number Pad Enter", "KPDOT": "Number Pad .",
    "MACRO1": "G1", "MACRO2": "G2", "MACRO3": "G3", "MACRO4": "G4", "MACRO5": "G5",
}.items():
    c = getattr(ecodes, "KEY_" + code, None)
    if c is not None:
        KEYNAME[c] = name


def find_keyboards():
    """The G915's typing input devices (not its mouse/consumer-control nodes)."""
    found = {}
    for path in evdev.list_devices():
        try:
            d = evdev.InputDevice(path)
        except OSError:
            continue
        keys = d.capabilities().get(ecodes.EV_KEY, [])
        if NAME.lower() in d.name.lower() and ecodes.KEY_A in keys:
            found[d.fd] = d
        else:
            d.close()
    return found


def main():
    client = OpenRGBClient(HOST, PORT, "keyripple")
    devs = [d for d in client.devices if NAME.lower() in d.name.lower()
            and d.type == DeviceType.KEYBOARD]
    if not devs:
        print(f"keyripple: no {NAME} keyboard in OpenRGB", file=sys.stderr)
        sys.exit(1)
    rgb = []
    for dev in devs:
        dev.set_mode("Direct")
        # LED index -> position, for the keys we know where they are
        pos = {}
        for i, led in enumerate(dev.leds):
            n = led.name[5:] if led.name.startswith("Key: ") else led.name
            if n in POS:
                pos[i] = POS[n]
        rgb.append((dev, pos))

    base = RGBColor(*BASE)

    def paint(ripples, now):
        for dev, pos in rgb:
            colors = []
            for i in range(len(dev.leds)):
                p = pos.get(i)
                w = 0.0
                if p is not None:
                    for (x, y, t0) in ripples:
                        a = (now - t0) / LIFE
                        if a >= 1:
                            continue
                        r = RADIUS * a
                        d = math.hypot(p[0] - x, p[1] - y)
                        w = max(w, (1 - a) ** 1.5 * math.exp(-((d - r) ** 2) / (2 * WIDTH ** 2)))
                if w <= 0.01:
                    colors.append(base)
                else:
                    w = min(w, 1.0)
                    colors.append(RGBColor(*(int(BASE[k] + (GOLD[k] - BASE[k]) * w) for k in range(3))))
            dev.set_colors(colors, fast=True)

    paint([], time.monotonic())
    kbds = find_keyboards()
    if DEBUG:
        print("keyboards", [d.name for d in kbds.values()], "leds", [len(p) for _, p in rgb], flush=True)
    ripples = []
    last_scan = time.monotonic()
    active = False
    while True:
        now = time.monotonic()
        if now - last_scan > 3:
            for d in kbds.values():
                d.close()
            kbds = find_keyboards()
            last_scan = now
        timeout = 1 / FPS if ripples else 1.0
        try:
            ready, _, _ = select.select(list(kbds), [], [], timeout)
        except (OSError, ValueError):
            kbds = {}
            continue
        for fd in ready:
            try:
                for ev in kbds[fd].read():
                    if ev.type == ecodes.EV_KEY and ev.value == 1:
                        name = KEYNAME.get(ev.code)
                        if name in POS:
                            x, y = POS[name]
                            ripples.append((x, y, time.monotonic()))
                            if DEBUG:
                                print("ripple", len(ripples), flush=True)
            except OSError:
                kbds.pop(fd, None)
        now = time.monotonic()
        ripples = [r for r in ripples if now - r[2] < LIFE][-24:]
        if ripples:
            paint(ripples, now)
            active = True
        elif active:
            paint([], now)
            active = False


if __name__ == "__main__":
    main()

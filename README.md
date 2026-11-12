# Key Ripple

A soft, warm-gold ripple on a Logitech G915 keyboard every time a key is pressed. The rest
of the keys stay a soft teal.

Needs a running [OpenRGB](https://openrgb.org) server (default `127.0.0.1:6742`) and read
access to the keyboard's `/dev/input` device. Only *which* key was pressed is used, to place
the ripple. Nothing is stored or logged.

    python3 keyripple.py      # needs the python packages openrgb-python and evdev

Settings, all optional, as environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `KEYRIPPLE_BASE` | `00483F` | resting colour of the keys |
| `KEYRIPPLE_RIPPLE` | `BE7A1E` | ripple colour |
| `KEYRIPPLE_RADIUS` | `3.0` | how far a ripple spreads, in keys |
| `KEYRIPPLE_LIFE` | `1.1` | how long a ripple lasts, in seconds |
| `KEYRIPPLE_DEVICE` | `G915` | part of the keyboard's name |
| `KEYRIPPLE_DEBUG` | unset | print the keyboards found and a count of ripples |

On blaney-pc it runs as the `keyripple` system service (nixos-config, `pkgs/keyripple`).

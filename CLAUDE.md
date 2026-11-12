# Key Ripple

*Created for insideabush on 2026-11-12. Keep the two sections below current as the app grows.*

> **The rules for working here are in `../CLAUDE.md`.**

## What this app is

A gold ripple on his G915 keyboard on every key press, over a soft teal base (his picks:
warm gold, small then "just a little larger" (3 keys), slow and gentle (~1.1 s)). One file,
`keyripple.py`: reads key presses with evdev, paints per-key colours through the OpenRGB
server in Direct mode. OpenRGB has no layout map for the G915, so the key positions are a
table in the file. The keyboard's own "Reactive (Ripple)" mode was tried first: it is rainbow
and spreads across the whole board, which he found distracting.

## Where things stand

Works wired. Runs on blaney-pc as the `keyripple` system service (nixos-config
`pkgs/keyripple`), restarted along with OpenRGB.

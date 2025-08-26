#!/usr/bin/env python3
# Runs a script whenever GNOME reports "screen unlocked".
import os, subprocess
from gi.repository import GLib
from pydbus import SessionBus

SCRIPT = os.path.expanduser("~/.local/bin/my-script.py")  # <--- change if needed

bus = SessionBus()
loop = GLib.MainLoop()
state = {"locked": None}

def on_active_changed(locked):
    # GNOME emits True when locked, False when unlocked
    prev = state["locked"]
    state["locked"] = locked
    if prev is True and locked is False:
        # transitioned: locked -> unlocked
        try:
            subprocess.Popen([SCRIPT], close_fds=True)
        except Exception as e:
            with open(os.path.expanduser("~/.cache/run-on-unlock.log"), "a") as f:
                f.write(f"Error: {e}\n")

bus.subscribe(
    iface="org.gnome.ScreenSaver",
    signal="ActiveChanged",
    signal_fired=lambda *args, **kwargs: on_active_changed(args[0])
)

loop.run()

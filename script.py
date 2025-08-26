#!/usr/bin/env python3
import argparse
import re
import shutil
import signal
import subprocess
import sys
import time

def parse_duration(s: str, default_minutes: int) -> float:
    if not s:
        return default_minutes * 60
    m = re.fullmatch(r"\s*(\d+)\s*([smh]?)\s*", s, re.I)
    if not m:
        raise SystemExit(f"Invalid duration: {s!r} (use like 45m, 15m, 3600s)")
    n, unit = int(m.group(1)), (m.group(2) or "m").lower()
    if unit == "s": return float(n)
    if unit == "m": return float(n * 60)
    if unit == "h": return float(n * 3600)
    raise SystemExit(f"Invalid unit in duration: {s!r}")

def notify(title: str, body: str = "") -> None:
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", title, body], check=False)
    else:
        print(f"[NOTIFY] {title} - {body}", flush=True)

def try_cmd(cmd):
    try:
        return subprocess.run(cmd, check=False).returncode == 0
    except Exception:
        return False

def lock_session() -> bool:
    # Try a few common lock methods; first one that works wins.
    # systemd/logind (most distros)
    if try_cmd(["loginctl", "lock-session"]): return True
    # GNOME (D-Bus)
    if try_cmd(["gdbus","call","--session","--dest","org.gnome.ScreenSaver",
                "--object-path","/org/gnome/ScreenSaver",
                "--method","org.gnome.ScreenSaver.Lock"]): return True
    # GNOME (legacy)
    if try_cmd(["gnome-screensaver-command","-l"]): return True
    # XDG fallback (some DEs implement this)
    if try_cmd(["xdg-screensaver","lock"]): return True
    # LightDM
    if try_cmd(["dm-tool","lock"]): return True
    # XScreenSaver
    if try_cmd(["xscreensaver-command","-lock"]): return True
    return False

def graceful_exit(signum, frame):
    print(f"\nReceived signal {signum}; exiting.", flush=True)
    sys.exit(0)

def main():
    ap = argparse.ArgumentParser(description="Simple focus→warn→lock timer.")
    ap.add_argument("--focus", default="45m",
                    help="focus duration before warning (e.g., 45m, 2700s, 1h)")
    ap.add_argument("--grace", default="15m",
                    help="grace duration after warning before lock")
    args = ap.parse_args()

    focus_s = parse_duration(args.focus, 45)
    grace_s = parse_duration(args.grace, 15)

    # Handle Ctrl+C / termination nicely
    signal.signal(signal.SIGINT, graceful_exit)
    signal.signal(signal.SIGTERM, graceful_exit)

    print(f"Focus for {int(focus_s)}s → warn → {int(grace_s)}s → lock", flush=True)

    t0 = time.monotonic()
    # Focus period
    while True:
        remaining = focus_s - (time.monotonic() - t0)
        if remaining <= 0:
            break
        time.sleep(min(1.0, max(0.0, remaining)))

    notify("Time to take a break 🤸", "You’ve hit your focus limit. 15 min until auto-lock.")

    # Grace period
    g0 = time.monotonic()
    while True:
        remaining = grace_s - (time.monotonic() - g0)
        if remaining <= 0:
            break
        time.sleep(min(1.0, max(0.0, remaining)))

    # Lock
    if lock_session():
        print("Locked the session.", flush=True)
    else:
        notify("Auto-lock failed", "Couldn’t lock the session automatically.")
        print("WARNING: Lock command failed; install/choose a compatible locker.", flush=True)

if __name__ == "__main__":
    main()

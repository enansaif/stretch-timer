#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import platform

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# --- helpers ---

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

def try_cmd(cmd):
    try:
        return subprocess.run(cmd, check=False).returncode == 0
    except Exception:
        return False

# --- notifications (Linux + Windows) ---

def notify(title: str, body: str = "") -> None:
    if IS_LINUX:
        if shutil.which("notify-send"):
            subprocess.run(["notify-send", title, body], check=False)
        else:
            print(f"[NOTIFY] {title} - {body}", flush=True)
        return

    if IS_WINDOWS:
        # Try SnoreToast (portable toast exe) if present on PATH
        if shutil.which("snoretoast.exe"):
            subprocess.run(["snoretoast.exe", "-t", title, "-m", body], check=False)
            return
        # Try PowerShell BurntToast module if available
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if ps:
            cmd = [
                ps, "-NoProfile", "-Command",
                # Fire-and-forget toast; ignore errors if BurntToast isn't installed
                "Try { "
                "Import-Module BurntToast -ErrorAction Stop; "
                f"New-BurntToastNotification -Text @('{title}','{body}') "
                "} Catch {{}}"
            ]
            subprocess.run(cmd, check=False)
            return
        # Last resort: console
        print(f"[NOTIFY] {title} - {body}", flush=True)
        return

    # Other OSes: console fallback
    print(f"[NOTIFY] {title} - {body}", flush=True)

# --- lock / lock-state (Linux + Windows) ---

def lock_session() -> bool:
    if IS_LINUX:
        # Try a few common lock methods; first one that works wins.
        if try_cmd(["loginctl", "lock-session"]): return True
        if try_cmd(["gdbus","call","--session","--dest","org.gnome.ScreenSaver",
                    "--object-path","/org/gnome/ScreenSaver",
                    "--method","org.gnome.ScreenSaver.Lock"]): return True
        if try_cmd(["gnome-screensaver-command","-l"]): return True
        if try_cmd(["xdg-screensaver","lock"]): return True
        if try_cmd(["dm-tool","lock"]): return True
        if try_cmd(["xscreensaver-command","-lock"]): return True
        return False

    if IS_WINDOWS:
        # Use Win32 API: LockWorkStation
        try:
            import ctypes
            ok = ctypes.windll.user32.LockWorkStation()
            return bool(ok)
        except Exception:
            # Fallback via rundll32 (rarely needed)
            return try_cmd(["rundll32.exe", "user32.dll,LockWorkStation"])

    return False

# --- lock state helpers ---

def _windows_input_desktop_name() -> str | None:
    """Return the current input desktop name ('Default' when unlocked, 'Winlogon' when locked)."""
    try:
        import ctypes
        from ctypes import wintypes

        UOI_NAME = 2
        DESKTOP_READOBJECTS = 0x0001
        DESKTOP_SWITCHDESKTOP = 0x0100

        user32 = ctypes.windll.user32

        # Open the desktop currently receiving user input
        hdesk = user32.OpenInputDesktop(0, False, DESKTOP_READOBJECTS | DESKTOP_SWITCHDESKTOP)
        if not hdesk:
            # If we cannot open the input desktop, assume locked (returns None to let caller decide)
            return None

        try:
            # Query size
            needed = wintypes.DWORD(0)
            user32.GetUserObjectInformationW(hdesk, UOI_NAME, None, 0, ctypes.byref(needed))
            buf = (ctypes.c_wchar * (needed.value // ctypes.sizeof(ctypes.c_wchar)))()
            if not user32.GetUserObjectInformationW(hdesk, UOI_NAME, buf, ctypes.sizeof(buf), ctypes.byref(needed)):
                return None
            return ctypes.wstring_at(buf)
        finally:
            user32.CloseDesktop(hdesk)
    except Exception:
        return None

def session_locked() -> bool:
    """Best-effort check if the current session is locked."""
    if IS_LINUX:
        sess = os.environ.get("XDG_SESSION_ID")
        if shutil.which("loginctl") and sess:
            try:
                r = subprocess.run(
                    ["loginctl", "show-session", sess, "-p", "LockedHint"],
                    capture_output=True, text=True, check=False
                )
                if "LockedHint=yes" in r.stdout:
                    return True
                if "LockedHint=no" in r.stdout:
                    return False
            except Exception:
                pass
        if shutil.which("gdbus"):
            try:
                r = subprocess.run(
                    ["gdbus","call","--session","--dest","org.gnome.ScreenSaver",
                     "--object-path","/org/gnome/ScreenSaver",
                     "--method","org.gnome.ScreenSaver.GetActive"],
                    capture_output=True, text=True, check=False
                )
                out = (r.stdout or "").lower()
                if "true" in out:  # " (true, )"
                    return True
                if "false" in out:
                    return False
            except Exception:
                pass
        return False  # unknown → assume unlocked

    if IS_WINDOWS:
        name = _windows_input_desktop_name()
        # Heuristic:
        #   - 'Default' → unlocked
        #   - 'Winlogon' → locked
        #   - None (couldn't query) → assume locked? We keep behavior consistent with Linux: assume unlocked
        if name is None:
            return False
        name = name.strip()
        if name.lower() == "winlogon":
            return True
        if name.lower() == "default":
            return False
        # If some other desktop is active (rare), be conservative and treat as unlocked
        return False

    # Other OSes: assume unlocked
    return False

def wait_until_unlocked(poll_interval: float = 1.0) -> None:
    """Block until the session is unlocked (best-effort)."""
    # If we have *some* way to tell lock state, poll it; otherwise just return
    can_detect = True
    if IS_LINUX and not (shutil.which("loginctl") or shutil.which("gdbus")):
        can_detect = False
    if IS_WINDOWS:
        # We try to detect via input desktop; if even that returns None every time, we'll still loop a bit
        can_detect = True

    if not can_detect:
        return

    while session_locked():
        time.sleep(poll_interval)

# --- one-cycle runner that aborts on manual lock ---

def run_one_cycle(focus_s: float, grace_s: float) -> None:
    notify("Focus started ✅", f"Focus {int(focus_s // 60)}m, then {int(grace_s // 60)}m grace.")
    print(f"Focus for {int(focus_s)}s → warn → {int(grace_s)}s → lock", flush=True)

    # Focus
    t0 = time.monotonic()
    while True:
        if session_locked():  # manual lock detected
            print("Detected manual lock during focus; waiting for unlock…", flush=True)
            wait_until_unlocked()
            print("Unlocked. Restarting timer…", flush=True)
            return  # abort this cycle and let caller restart fresh
        remaining = focus_s - (time.monotonic() - t0)
        if remaining <= 0:
            break
        time.sleep(min(1.0, max(0.0, remaining)))

    notify("Time to take a break 🤸", f"You’ve hit your focus limit. {int(grace_s // 60)}m until auto-lock.")

    # Grace
    g0 = time.monotonic()
    while True:
        if session_locked():             # manual lock during grace
            print("Detected manual lock during grace; waiting for unlock…", flush=True)
            wait_until_unlocked()
            print("Unlocked. Restarting timer…", flush=True)
            return
        remaining = grace_s - (time.monotonic() - g0)
        if remaining <= 0:
            break
        time.sleep(min(1.0, max(0.0, remaining)))

    # Auto-lock (script-initiated)
    if lock_session():
        print("Locked the session (auto).", flush=True)
    else:
        notify("Auto-lock failed", "Couldn’t lock the session automatically.")
        print("WARNING: Lock command failed; install/choose a compatible locker.", flush=True)

    # After script-initiated lock, wait for unlock, then return to restart
    wait_until_unlocked()
    print("Detected unlock. Restarting timer…", flush=True)

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

    # Signals: SIGTERM isn't always delivered on Windows, but this is harmless.
    try:
        signal.signal(signal.SIGINT, graceful_exit)
        signal.signal(signal.SIGTERM, graceful_exit)
    except Exception:
        pass

    # loop forever: restart after manual or auto unlock
    while True:
        run_one_cycle(focus_s, grace_s)

if __name__ == "__main__":
    main()

# Stretch-Timer
A simple Linux utility that promotes healthier screen time by reminding you to take regular breaks, stretch, and reset. It starts a focus session when you begin using your PC, notifies you after 45 minutes, and automatically locks your screen if you don’t take a break within the next 15 minutes.

---
# Stretch-Timer Service
Run script.py automatically at system startup on **Ubuntu Linux** using **systemd** (user-level service).

## Instructions (Ubuntu)
```bash
# 1. Clone the repository
git clone https://github.com/enansaif/stretch-timer.git
cd stretch-timer

# 2. Make sure the script is executable
chmod +x script.py

# 3. Create a user systemd service file
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/stretch-timer.service

# Paste the following into the file:
# ---------------------------------
# [Unit]
# Description=Focus → warn → lock timer
#
# [Service]
# ExecStart=<path-to-repo>/script.py --focus 45m --grace 15m
# Restart=always
#
# [Install]
# WantedBy=default.target
# ---------------------------------

# 4. Reload systemd and enable the service
systemctl --user daemon-reload
systemctl --user enable stretch-timer.service
systemctl --user start stretch-timer.service

# 5. Check service status
systemctl --user status stretch-timer.service

# Stop the service
systemctl --user stop stretch-timer.service

# Disable the service from starting at boot
systemctl --user disable stretch-timer.service
```

## Instructions (Windows)
Run `script.py` automatically at **user logon** on Windows 10/11 using **Task Scheduler**.
```bash
# 1. Clone the repository
cd $env:USERPROFILE
git clone https://github.com/enansaif/stretch-timer.git
cd stretch-timer

# 2. (Optional) Make notifications work
# Option A: Install SnoreToast (recommended)
choco install snoretoast -y
# Option B: Install BurntToast (PowerShell module)
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
Install-Module -Name BurntToast -Scope CurrentUser -Force

# 3. Create a scheduled task to run at logon
$PYW = "<path-to>\pythonw.exe" # use pythonw.exe to avoid console window
$SCRIPT = "<path-to-repo>\script.py"
schtasks /Create /TN "Stretch-Timer" /TR "'$PYW' '$SCRIPT' --focus 45m --grace 15m" /SC ONLOGON /RL LIMITED /F

# 4. Start it immediately (optional)
schtasks /Run /TN "Stretch-Timer"

# 5. Manage the task later
schtasks /Query /TN "Stretch-Timer" /V /FO LIST # check status
schtasks /End /TN "Stretch-Timer" # stop
schtasks /Delete /TN "Stretch-Timer" /F # remove
```

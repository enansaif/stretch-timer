# Stretch-Timer
A simple Linux utility that promotes healthier screen time by reminding you to take regular breaks, stretch, and reset. It starts a focus session when you begin using your PC, notifies you after 45 minutes, and automatically locks your screen if you don’t take a break within the next 15 minutes.

# Stretch-Timer Service: Run script.py automatically at system startup on **Ubuntu Linux** using systemd (user-level service). 

## Instructions (Ubuntu)
bash
# 1. Clone the repository
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# 2. Make sure the script is executable
chmod +x script.py

# 3. Create a user systemd service file
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/<servicename>.service

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
systemctl --user enable <servicename>.service
systemctl --user start <servicename>.service

# 5. Check service status
systemctl --user status <servicename>.service

# (Optional) Allow user services to run even without login
loginctl enable-linger $(whoami)

# Stop the service
systemctl --user stop <servicename>.service

# Disable the service from starting at boot
systemctl --user disable <servicename>.service

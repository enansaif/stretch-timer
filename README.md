# Stretch-Timer
A simple Linux utility that promotes healthier screen time by reminding you to take regular breaks, stretch, and reset.  
It starts a focus session when you begin using your PC, notifies you after 45 minutes, and automatically locks your screen if you don’t take a break within the next 15 minutes.

---

# Stretch-Timer Service
Run `script.py` automatically at system startup on **Ubuntu Linux** using **systemd** (user-level service).

## Instructions (Ubuntu)

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# 2. Make sure the script is executable
chmod +x script.py

# 3. Create a user systemd service file
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/stretch-timer.service << 'EOF'
[Unit]
Description=Focus → warn → lock timer

[Service]
# Update the path below to the absolute path of script.py in your repo
ExecStart=/home/<your-username>/<your-repo>/script.py --focus 45m --grace 15m
Restart=always

[Install]
WantedBy=default.target
EOF

# 4. Reload systemd and enable the service
systemctl --user daemon-reload
systemctl --user enable stretch-timer.service
systemctl --user start stretch-timer.service

# 5. Check service status
systemctl --user status stretch-timer.service

# (Optional) Allow user services to run even without login
loginctl enable-linger $(whoami)

# Stop the service
systemctl --user stop stretch-timer.service

# Disable the service from starting at boot
systemctl --user disable stretch-timer.service

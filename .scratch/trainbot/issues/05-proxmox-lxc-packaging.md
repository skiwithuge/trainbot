Type: task
Status: resolved
Blocked by: 04

# Proxmox LXC Service Packaging & Deployment

## Question

How should the Python application be packaged, configured with dependencies and environment variables, and configured as a resilient systemd daemon service inside a Proxmox LXC container (with auto-restart, log forwarding via journald, and an easy setup script)?

## Answer

Implemented complete LXC deployment suite:
1. **Systemd Unit ([deploy/trainbot.service](file:///home/skiwithuge/workspace/antigravity/trainbot/deploy/trainbot.service))**:
   - `Restart=always` with `RestartSec=5s` for automatic recovery if container restarts or network blips.
   - Loads environment variables directly from `/opt/trainbot/.env`.
   - Sends output directly to systemd journal (`journalctl -u trainbot -f`).
2. **Automated Installer ([deploy/install.sh](file:///home/skiwithuge/workspace/antigravity/trainbot/deploy/install.sh))**:
   - Verifies and installs system prerequisites (`python3`, `python3-venv`, `git`).
   - Copies files into `/opt/trainbot`, creates `.venv`, installs dependencies from `requirements.txt` and `pyproject.toml`.
   - Registers, enables, and prepares the systemd unit.
3. **Packaging ([pyproject.toml](file:///home/skiwithuge/workspace/antigravity/trainbot/pyproject.toml))**:
   - Standard PEP 621 packaging with `pip install -e .` and console entry point `trainbot`.
4. **Documentation ([README.md](file:///home/skiwithuge/workspace/antigravity/trainbot/README.md))**:
   - End-to-end setup guide with exact commands for Proxmox LXC, troubleshooting, and local testing.

#!/usr/bin/env bash
set -e
[ "$(id -u)" -eq 0 ] || { echo "Uruchom jako root (sudo)"; exit 1; }
SERVER="__URL__"
TOKEN="__TOKEN__"
DIR=/opt/homepulse-agent

echo "-> Instaluje agenta HomePulse (serwer: $SERVER)"
command -v python3 >/dev/null || { echo "Brak python3"; exit 1; }
mkdir -p "$DIR"
python3 -m venv "$DIR/venv" 2>/dev/null || { apt-get update -qq && apt-get install -y -qq python3-venv && python3 -m venv "$DIR/venv"; }
"$DIR/venv/bin/pip" install -q psutil
curl -fsSL "$SERVER/agent.py" -o "$DIR/agent.py"

cat > /etc/systemd/system/homepulse-agent.service <<UNIT
[Unit]
Description=HomePulse agent
After=network-online.target
Wants=network-online.target

[Service]
Environment=HOMEPULSE_SERVER=$SERVER
Environment=HOMEPULSE_TOKEN=$TOKEN
ExecStart=$DIR/venv/bin/python $DIR/agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now homepulse-agent
echo "OK: agent dziala, sprawdz dashboard"

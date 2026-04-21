#!/usr/bin/env bash
# ============================================================================
# Provision a Pi against a school. Run interactively once on the device.
# Fills in /etc/yuz-tanima/edge.env and enables the systemd service.
# ============================================================================
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Must be run as root" >&2
  exit 1
fi

ETC="/etc/yuz-tanima/edge.env"

read -rp "Device ID (UUID from SuperAdmin panel): " DEVICE_ID
read -rp "School ID: " SCHOOL_ID
read -rp "API Key: " -s API_KEY; echo
read -rp "Server URL [https://api.yuztanima.com]: " SERVER_URL
SERVER_URL="${SERVER_URL:-https://api.yuztanima.com}"

cat >"${ETC}" <<EOF
DEVICE_ID=${DEVICE_ID}
SCHOOL_ID=${SCHOOL_ID}
API_KEY=${API_KEY}
SERVER_URL=${SERVER_URL}

# Optional overrides — see edge/app/config.py
# RECOGNITION_TOLERANCE=0.55
# GPIO_RELAY_PIN=17
# RELAY_PULSE_MS=500
# LOG_LEVEL=INFO
EOF
chmod 600 "${ETC}"
chown yuztanima:yuztanima "${ETC}"

systemctl enable --now yuz-tanima-edge.service
systemctl --no-pager status yuz-tanima-edge.service || true

echo ""
echo "✅ Provisioning complete. Check logs:"
echo "   journalctl -u yuz-tanima-edge -f"
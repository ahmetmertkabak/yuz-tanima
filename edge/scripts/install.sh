#!/usr/bin/env bash
# ============================================================================
# Yüz Tanıma Edge Node — install script for Raspberry Pi OS (Bookworm, 64-bit)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/ahmetmertkabak/yuz-tanima/main/edge/scripts/install.sh | sudo bash
#   OR
#   sudo bash install.sh
#
# Creates:
#   - /opt/yuz-tanima/edge          — application code + virtualenv
#   - /etc/yuz-tanima/edge.env      — (empty placeholder; run provision.sh next)
#   - /var/log/yuz-tanima/          — log directory
#   - yuztanima system user
#   - systemd service (not started until provisioned)
# ============================================================================
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Must be run as root (use sudo)" >&2
  exit 1
fi

REPO_URL="${REPO_URL:-https://github.com/ahmetmertkabak/yuz-tanima.git}"
APP_USER="yuztanima"
APP_DIR="/opt/yuz-tanima"
EDGE_DIR="${APP_DIR}/edge"
ETC_DIR="/etc/yuz-tanima"
LOG_DIR="/var/log/yuz-tanima"

echo "==> Updating apt package index"
apt-get update -y

echo "==> Installing system dependencies"
apt-get install -y --no-install-recommends \
  git python3 python3-venv python3-pip python3-dev \
  build-essential cmake pkg-config \
  libatlas-base-dev libjpeg-dev libopenblas-dev \
  libgtk-3-0 libavcodec-dev libavformat-dev libswscale-dev \
  libv4l-dev v4l-utils \
  python3-opencv python3-dlib \
  i2c-tools

echo "==> Creating system user: ${APP_USER}"
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --home-dir "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
  usermod -aG video,gpio,i2c "${APP_USER}"
fi

echo "==> Cloning / updating repo"
mkdir -p "${APP_DIR}"
if [[ -d "${APP_DIR}/.git" ]]; then
  git -C "${APP_DIR}" pull --ff-only
else
  git clone "${REPO_URL}" "${APP_DIR}"
fi

echo "==> Creating Python virtualenv"
python3 -m venv "${EDGE_DIR}/.venv" --system-site-packages
"${EDGE_DIR}/.venv/bin/pip" install --upgrade pip wheel
"${EDGE_DIR}/.venv/bin/pip" install -r "${EDGE_DIR}/requirements.txt"

echo "==> Creating /etc dir and placeholder env"
mkdir -p "${ETC_DIR}"
if [[ ! -f "${ETC_DIR}/edge.env" ]]; then
  cat >"${ETC_DIR}/edge.env" <<'EOF'
# Filled in by provision.sh
DEVICE_ID=
SCHOOL_ID=
API_KEY=
SERVER_URL=https://api.yuztanima.com
EOF
  chmod 600 "${ETC_DIR}/edge.env"
fi

echo "==> Creating log dir"
mkdir -p "${LOG_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}" "${ETC_DIR}" "${LOG_DIR}"

echo "==> Installing systemd unit"
install -m 644 "${EDGE_DIR}/systemd/yuz-tanima-edge.service" \
  /etc/systemd/system/yuz-tanima-edge.service
systemctl daemon-reload

echo ""
echo "✅ Install complete."
echo "Next step:  sudo bash ${EDGE_DIR}/scripts/provision.sh"
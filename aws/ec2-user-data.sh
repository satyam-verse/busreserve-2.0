#!/usr/bin/env bash
# BusReserve 2.0 — AWS EC2 Cloud-Init Bootstrap Script (Ubuntu 24.04 LTS)
# Zero-Cost Free Tier Automated Instance Provisioner (t2.micro / t3.micro)
set -euo pipefail

echo "=== [1/6] Updating system packages & configuring 2GB Swap for Free Tier ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y && apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg lsb-release ufw git jq

# t2.micro / t3.micro has 1GB RAM; add 2GB swap space to ensure smooth Docker builds & operations
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "=== [2/6] Installing official Docker CE & Docker Compose Plugin ==="
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker
usermod -aG docker ubuntu

echo "=== [3/6] Hardening Host Firewall (UFW) ==="
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw --force enable

echo "=== [4/6] Setting up BusReserve Application Directory ==="
APP_DIR="/opt/busreserve"
mkdir -p "${APP_DIR}"
chown -R ubuntu:ubuntu "${APP_DIR}"

# Clone repository (operator provides token or public URL)
REPO_URL="${1:-https://github.com/your-org/busreserve.git}"
if [ ! -d "${APP_DIR}/.git" ]; then
    git clone "${REPO_URL}" "${APP_DIR}" || true
fi

cd "${APP_DIR}"

echo "=== [5/6] Preparing Production Environment Configuration ==="
if [ ! -f .env ]; then
    cp .env.example .env
    RAND_SECRET=$(openssl rand -hex 32)
    RAND_JWT=$(openssl rand -hex 32)
    sed -i "s/replace-with-strong-random-secret-32b/${RAND_SECRET}/" .env
    sed -i "s/replace-with-strong-jwt-secret-32b/${RAND_JWT}/" .env
    sed -i "s/COOKIE_SECURE=false/COOKIE_SECURE=true/" .env
    sed -i "s/SEED_ON_STARTUP=true/SEED_ON_STARTUP=false/" .env
fi

echo "=== [6/6] Launching Production Multi-Container Stack ==="
docker compose -f docker-compose.prod.yml up -d

echo "=== BusReserve 2.0 Cloud Bootstrap Complete ==="
docker compose ps

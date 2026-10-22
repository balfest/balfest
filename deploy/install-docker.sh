#!/usr/bin/env bash
# Idempotent Docker Engine + Compose installation for dedicated Ubuntu runners.
set -Eeuo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "::error::Run as root, e.g. sudo -n bash deploy/install-docker.sh" >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  echo "::error::Unsupported Linux: missing /etc/os-release" >&2
  exit 1
fi
source /etc/os-release
if [[ "$ID" != "ubuntu" ]]; then
  echo "::error::This installer supports Ubuntu only (found: $ID)." >&2
  exit 1
fi
if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "::error::The workflow runner is configured for Linux x86_64 only." >&2
  exit 1
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  if ! systemctl is-active --quiet docker; then
    systemctl enable --now docker
  fi
  if docker info >/dev/null 2>&1; then
    echo "Docker Engine and Compose are already available."
    docker --version
    docker compose version
    exit 0
  fi
fi

# Don't silently uninstall an existing distribution Docker installation.
if dpkg-query -W -f='${Status}' docker.io 2>/dev/null | grep -q 'install ok installed'; then
  echo "::error::Ubuntu's docker.io is installed but Docker Engine/Compose is not healthy." >&2
  echo "::error::Resolve the package conflict manually before running this workflow." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $VERSION_CODENAME
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

docker version
docker compose version
docker info >/dev/null
echo "Docker Engine and Compose installed and verified."

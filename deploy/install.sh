#!/usr/bin/env bash
set -euo pipefail

# SNCF Train Bot Proxmox LXC Installer
# Target directory: /opt/trainbot

INSTALL_DIR="/opt/trainbot"
SERVICE_NAME="trainbot.service"

echo "=== Installation du bot SNCF TrainBot dans /opt/trainbot ==="

# 1. Installer les prérequis système (Debian/Ubuntu)
if command -v apt-get &>/dev/null; then
    echo "-> Mise à jour des paquets et installation de Python3 et venv..."
    apt-get update -y
    apt-get install -y python3 python3-venv python3-pip git
fi

# 2. Créer le répertoire d'installation s'il n'existe pas
mkdir -p "${INSTALL_DIR}"

# 3. Copier les fichiers du bot vers /opt/trainbot si lancé depuis un autre dossier
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ "${SOURCE_DIR}" != "${INSTALL_DIR}" ]; then
    echo "-> Copie des sources vers ${INSTALL_DIR}..."
    cp -r "${SOURCE_DIR}/src" "${INSTALL_DIR}/"
    cp -r "${SOURCE_DIR}/deploy" "${INSTALL_DIR}/"
    cp "${SOURCE_DIR}/requirements.txt" "${INSTALL_DIR}/"
    cp "${SOURCE_DIR}/pyproject.toml" "${INSTALL_DIR}/"
    cp "${SOURCE_DIR}/.env.example" "${INSTALL_DIR}/"
    if [ -f "${SOURCE_DIR}/.env" ] && [ ! -f "${INSTALL_DIR}/.env" ]; then
        cp "${SOURCE_DIR}/.env" "${INSTALL_DIR}/.env"
    fi
fi

# 4. Configuration de l'environnement virtuel Python
echo "-> Création de l'environnement virtuel Python..."
cd "${INSTALL_DIR}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo "-> Installation des dépendances Python..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .

# 5. Préparation du fichier .env
if [ ! -f ".env" ]; then
    echo "-> Création du fichier .env depuis le modèle .env.example..."
    cp .env.example .env
    echo "⚠️ N'oubliez pas d'éditer ${INSTALL_DIR}/.env avec vos clés réelles !"
fi

# 6. Installation et activation du service systemd
echo "-> Installation du service systemd..."
cp "${INSTALL_DIR}/deploy/${SERVICE_NAME}" "/etc/systemd/system/${SERVICE_NAME}"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

echo ""
echo "=== ✅ Installation terminée avec succès ! ==="
echo "1. Éditez votre fichier de configuration :"
echo "   nano ${INSTALL_DIR}/.env"
echo ""
echo "2. Démarrez le bot :"
echo "   systemctl start ${SERVICE_NAME}"
echo ""
echo "3. Consultez les logs en direct :"
echo "   journalctl -u ${SERVICE_NAME} -f"

#!/bin/bash
#
# FF-Tracker Uninstallation Script
# Removes the Fantasy Football Tracker from the system
#

set -e

# Configuration
APP_NAME="ff-tracker"
APP_DIR="/opt/ff-tracker"
APP_USER="ff-tracker"
SERVICE_FILE="/etc/systemd/system/ff-tracker.service"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

echo
echo "=============================================="
echo "  FF-Tracker Uninstallation"
echo "=============================================="
echo
log_warning "This will completely remove FF-Tracker from your system."
echo
echo "The following will be removed:"
echo "  - Application directory: $APP_DIR"
echo "  - System user: $APP_USER"
echo "  - Systemd service: ff-tracker.service"
echo
read -p "Do you want to backup the database before uninstalling? (Y/n): " -n 1 -r BACKUP_REPLY
echo

if [[ ! $BACKUP_REPLY =~ ^[Nn]$ ]]; then
    if [[ -f "$APP_DIR/data/database.db" ]]; then
        BACKUP_FILE="$HOME/ff-tracker-backup-$(date +%Y%m%d-%H%M%S).db"
        cp "$APP_DIR/data/database.db" "$BACKUP_FILE"
        log_success "Database backed up to: $BACKUP_FILE"
    else
        log_warning "No database found to backup"
    fi
fi

read -p "Are you sure you want to uninstall FF-Tracker? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Uninstallation cancelled"
    exit 0
fi

# Stop and disable service
log_info "Stopping FF-Tracker service..."
systemctl stop ff-tracker.service 2>/dev/null || true
systemctl disable ff-tracker.service 2>/dev/null || true

# Remove service file
if [[ -f "$SERVICE_FILE" ]]; then
    rm -f "$SERVICE_FILE"
    systemctl daemon-reload
    log_success "Systemd service removed"
fi

# Remove application directory
if [[ -d "$APP_DIR" ]]; then
    log_info "Removing application directory..."
    rm -rf "$APP_DIR"
    log_success "Application directory removed"
fi

# Remove user
if id "$APP_USER" &>/dev/null; then
    log_info "Removing application user..."
    userdel "$APP_USER" 2>/dev/null || true
    log_success "User '$APP_USER' removed"
fi

# Ask about Cloudflare
if systemctl is-active --quiet cloudflared 2>/dev/null || systemctl is-enabled --quiet cloudflared 2>/dev/null; then
    echo
    read -p "Do you also want to remove Cloudflare Tunnel? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Removing Cloudflare Tunnel..."
        systemctl stop cloudflared 2>/dev/null || true
        systemctl disable cloudflared 2>/dev/null || true
        cloudflared service uninstall 2>/dev/null || true
        apt-get remove -y cloudflared 2>/dev/null || true
        rm -f /etc/apt/sources.list.d/cloudflared.list
        log_success "Cloudflare Tunnel removed"
    fi
fi

echo
echo "=============================================="
log_success "FF-Tracker has been uninstalled"
echo "=============================================="
echo

if [[ -n "$BACKUP_FILE" && -f "$BACKUP_FILE" ]]; then
    echo "Your database backup is at: $BACKUP_FILE"
    echo
fi

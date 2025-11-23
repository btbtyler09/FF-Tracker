#!/bin/sh
set -e

echo "=========================================="
echo "Fantasy Football Tracker - Starting Up"
echo "=========================================="
echo "Timestamp: $(date)"
echo "Current user: $(whoami) (UID: $(id -u), GID: $(id -g))"

# Fix permissions for data and logs directories if running as root
if [ "$(id -u)" = "0" ]; then
    echo ""
    echo "Running as root - fixing permissions for nobody user..."
    
    # Ensure directories exist
    mkdir -p /app/data /app/logs
    
    # Fix ownership for nobody:users (99:100)
    chown -R 99:100 /app/data /app/logs
    chmod 755 /app/data /app/logs
    
    echo "Permissions fixed, directories now owned by nobody:users"
fi

# Show directory status
echo ""
echo "Directory Status:"
ls -ld /app/data 2>/dev/null || echo "/app/data not yet created"
ls -ld /app/logs 2>/dev/null || echo "/app/logs not yet created"

echo ""
echo "Data directory contents:"
ls -la /app/data 2>/dev/null || echo "  (empty or not yet created)"

echo ""
echo "Seed data available:"
ls -la /app/seed_data 2>/dev/null || echo "  (no seed data found)"

echo ""
echo "=========================================="
echo "Starting Gunicorn Application Server..."
echo "=========================================="

# Execute the main command as root (permissions already fixed)
exec "$@"
#!/bin/bash
# Fantasy Football Tracker startup script

set -e

echo "Starting Fantasy Football Tracker..."

# Check if database exists and initialize if needed
if [ ! -f "/app/data/database.db" ]; then
    echo "Database not found. Initializing..."
    python import_data.py
fi

# Run the application
if [ "$FLASK_ENV" = "development" ]; then
    echo "Running in development mode..."
    python app.py
else
    echo "Running in production mode with gunicorn..."
    exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --keep-alive 2 app:app
fi
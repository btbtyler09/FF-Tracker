# Fantasy Football Tracker Dockerfile

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories for volume mounts
RUN mkdir -p /app/data /app/logs

# Set permissions
RUN chmod +x import_data.py update_scores.py docker-entrypoint.sh run_as_nobody.py

# Set database to use absolute path for clarity
ENV DATABASE_URL=sqlite:////app/data/database.db

# Create user compatible with Unraid (nobody:users = 99:100)
RUN groupadd -g 100 users || true
RUN useradd -u 99 -g 100 -s /bin/bash nobody || usermod -u 99 -g 100 nobody
RUN chown -R 99:100 /app

# Don't switch to nobody yet - entrypoint needs to fix permissions first
# USER nobody will be handled in entrypoint

# Expose port
EXPOSE 8742

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8742/health || exit 1

# Use entrypoint to fix permissions and provide logging
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command - use Python wrapper to drop privileges then run gunicorn
CMD ["python", "run_as_nobody.py", "gunicorn", "--bind", "0.0.0.0:8742", "--workers", "2", "--timeout", "120", "--keep-alive", "2", "app:app"]
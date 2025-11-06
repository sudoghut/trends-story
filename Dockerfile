# ==============================================================================
# Trends Story - Automated Execution Container
# ==============================================================================
# This Dockerfile creates a containerized environment for running the trends-story
# application on a scheduled or immediate basis. The container is designed to
# run autonomously, fetching trending topics and generating stories.
#
# Build: docker build -t trends-story:latest .
# Run (immediate): docker run -v $(pwd):/app/trends-story trends-story:latest
# Run (scheduled): docker run -d -v $(pwd):/app/trends-story trends-story:latest
# ==============================================================================

# Stage 1: Base image with system dependencies
FROM fedora:latest

# Metadata labels
LABEL maintainer="trends-story-team"
LABEL description="Automated trending story generation container with scheduled execution support"
LABEL version="1.0.0"
LABEL application="trends-story"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=America/New_York \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# - Python 3 and pip for running the application
# - git for repository operations and version control
# - cronie for cron-based scheduling
# - tzdata for timezone configuration
# - findutils for system utilities
RUN dnf update -y && \
    dnf install -y \
    python3 \
    python3-pip \
    git \
    cronie \
    tzdata \
    findutils \
    procps-ng \
    && dnf clean all \
    && rm -rf /var/cache/dnf/*

# Set timezone to America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# Create application directory structure
WORKDIR /app/trends-story

# Create necessary directories
# - /var/log/trends-story for application logs
# - /var/run/crond for cron daemon
RUN mkdir -p /var/log/trends-story && \
    mkdir -p /var/run/crond && \
    mkdir -p /app/trends-story

# Install Python dependencies
# Note: Currently no requirements.txt file exists in the repository
# Dependencies from README.md: serpapi, websockets, websocket-client
# These will be installed via pip when the container runs
RUN pip3 install --no-cache-dir \
    serpapi \
    websockets \
    websocket-client \
    pyyaml \
    wordcloud

# Set proper permissions for cron and log directories
# Allow cronie to run and write logs
RUN chmod 755 /var/log/trends-story && \
    chmod 755 /var/run/crond

# Configure cron to log output
RUN touch /var/log/trends-story/cron.log && \
    chmod 644 /var/log/trends-story/cron.log

# Health check configuration
# Checks for the .last_run timestamp file to verify the application is running
# If the file is older than 24 hours, the container is considered unhealthy
HEALTHCHECK --interval=1h --timeout=10s --start-period=30s --retries=3 \
    CMD test -f /app/trends-story/.last_run && \
        test $(find /app/trends-story/.last_run -mmin -1440 2>/dev/null | wc -l) -gt 0 || exit 1

# Volume mount point documentation
# The repository should be mounted here for the container to access source code
VOLUME ["/app/trends-story"]

# Copy entrypoint script (to be created in a later task)
# This script will handle both immediate and scheduled execution modes
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set the entrypoint
# The entrypoint.sh script will:
# - Check the run_mode from config.yaml
# - Either run immediately and exit, or set up cron scheduling
# - Handle proper signal forwarding and graceful shutdown
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command (can be overridden)
CMD []

# ==============================================================================
# Usage Notes:
# ==============================================================================
# 
# Build the image:
#   docker build -t trends-story:latest .
#
# Run in immediate mode (runs once and exits):
#   docker run --rm -v $(pwd):/app/trends-story trends-story:latest
#
# Run in scheduled mode (runs continuously with cron):
#   docker run -d --name trends-story-scheduled \
#     -v $(pwd):/app/trends-story \
#     trends-story:latest
#
# View logs:
#   docker logs trends-story-scheduled
#   docker exec trends-story-scheduled cat /var/log/trends-story/cron.log
#
# Stop the container:
#   docker stop trends-story-scheduled
#
# Requirements:
#   - The repository must be mounted as a volume at /app/trends-story
#   - config.yaml must exist on the HOST (not in the image) with run_mode and
#     cron_schedule configured. Create it from config.example.yaml:
#       cp config.example.yaml config.yaml
#       # Edit config.yaml and add your git_token
#   - entrypoint.sh must be present in the repository root
#
# IMPORTANT: config.yaml is gitignored and contains sensitive credentials.
# It must be created manually on each deployment environment and mounted
# into the container via the volume mount.
# ==============================================================================
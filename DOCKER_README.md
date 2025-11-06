# 🐋 Docker Container for Automated Python GitHub Repo Execution

[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Fedora](https://img.shields.io/badge/Fedora-51A2DA?style=flat&logo=fedora&logoColor=white)](https://getfedora.org/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Cron](https://img.shields.io/badge/Cron-Scheduled-green)](https://en.wikipedia.org/wiki/Cron)

A fully containerized, automated execution environment for the [trends-story](https://github.com/sudoghut/trends-story) repository. This Docker setup enables scheduled or immediate execution of trending story generation with automated Git synchronization.

---

## ✨ Features

- **🔧 Fedora-based Container** - Reliable, stable Linux environment with DNF package management
- **⏰ Automated Scheduling** - Flexible cron-based execution with customizable schedules
- **🔐 Git Token Authentication** - Secure GitHub operations with Personal Access Token
- **📝 Dual Logging System** - Simultaneous output to stdout and rotating log files
- **💚 Health Monitoring** - Built-in health checks to verify container and script execution
- **🚀 Dual Execution Modes** - Switch between scheduled (continuous) and immediate (one-time) modes
- **🔒 Concurrency Protection** - Lockfile mechanism prevents overlapping executions
- **🔄 Network Retry Logic** - Automatic retry with exponential backoff for network operations
- **🌍 Timezone Support** - Configured for America/New_York timezone (customizable)
- **📦 Volume Persistence** - All data, logs, and images persist outside the container

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (version 20.10 or later) - [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** (version 1.29 or later) - [Install Docker Compose](https://docs.docker.com/compose/install/)
- **GitHub Personal Access Token** - [Create a token](https://github.com/settings/tokens)
- **Basic understanding** of Docker, cron syntax, and Git operations

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/sudoghut/trends-story.git
cd trends-story
```

### 2. Configure Settings

Copy the example configuration file and add your GitHub token:

```bash
cp config.example.yaml config.yaml
```

Edit [`config.yaml`](config.yaml) and replace `YOUR_GITHUB_PERSONAL_ACCESS_TOKEN_HERE` with your actual token:

```yaml
git_token: "ghp_your_actual_token_here"
run_mode: "scheduled"
cron_schedule: "0 5,16 * * *"
```

### 3. Build and Run

**Option A: Using Docker Compose (Recommended)**

```bash
# Build the image
docker-compose build

# Start in background (scheduled mode)
docker-compose up -d

# View logs
docker-compose logs -f
```

**Option B: Using Docker Directly**

```bash
# Build the image
docker build -t trends-story:latest .

# Run in scheduled mode
docker run -d --name trends-story-automation \
  -v $(pwd):/app/trends-story \
  trends-story:latest
```

---

## ⚙️ Configuration

### Configuration File: [`config.yaml`](config.yaml)

The container behavior is controlled by the [`config.yaml`](config.yaml) file. Use [`config.example.yaml`](config.example.yaml) as a reference.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `git_token` | string | ✅ Yes | GitHub Personal Access Token for repository authentication |
| `run_mode` | string | ✅ Yes | Execution mode: `"scheduled"` or `"immediate"` |
| `cron_schedule` | string | Only for scheduled mode | Cron expression in 5 or 6 field format |
| `git_user_name` | string | ❌ No | Git commit author name (default: "Trends Story Bot") |
| `git_user_email` | string | ❌ No | Git commit author email (default: "bot@trends-story.local") |

### Getting a GitHub Personal Access Token

1. Navigate to [GitHub Settings → Tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (classic)"**
3. Provide a descriptive name (e.g., "Trends Story Automation")
4. Select **expiration** (recommend 90 days or custom)
5. **Required scopes**:
   - For public repos: ✅ `public_repo`
   - For private repos: ✅ `repo` (full control)
6. Click **"Generate token"** and copy immediately (you won't see it again!)
7. Add to your [`config.yaml`](config.yaml)

⚠️ **Security Warning**: Never commit [`config.yaml`](config.yaml) with real tokens to version control!

### Cron Schedule Examples

The `cron_schedule` field uses standard cron syntax with 5 fields:

```
┌───────────── minute (0-59)
│ ┌─────────── hour (0-23, America/New_York timezone)
│ │ ┌───────── day of month (1-31)
│ │ │ ┌─────── month (1-12)
│ │ │ │ ┌───── day of week (0-7, Sunday = 0 or 7)
│ │ │ │ │
* * * * *
```

**Common Schedule Examples:**

```yaml
# Every day at 5 AM and 4 PM NY time (default)
cron_schedule: "0 5,16 * * *"

# Every 6 hours
cron_schedule: "0 */6 * * *"

# Daily at midnight
cron_schedule: "0 0 * * *"

# Weekdays at 8:30 AM
cron_schedule: "30 8 * * 1-5"

# Every 4 hours
cron_schedule: "0 */4 * * *"

# Four times daily (9 AM, 12 PM, 3 PM, 6 PM)
cron_schedule: "0 9,12,15,18 * * *"
```

---

## 📖 Usage

### Scheduled Mode (Default)

Runs continuously with automated cron-based scheduling. The container stays running and executes the script according to your cron schedule.

**Start the container:**

```bash
# Using docker-compose
docker-compose up -d

# Using docker directly
docker run -d --name trends-story-automation \
  -v $(pwd):/app/trends-story \
  trends-story:latest
```

**Manage the container:**

```bash
# View logs in real-time
docker-compose logs -f

# View last 100 log lines
docker-compose logs --tail=100

# Stop the container
docker-compose down

# Restart the container
docker-compose restart

# Check container status
docker-compose ps
```

### Immediate Mode (Testing)

Runs once and exits immediately. Perfect for testing before deploying scheduled mode.

**1. Update [`config.yaml`](config.yaml):**

```yaml
run_mode: "immediate"
```

**2. Run the container:**

```bash
# Using docker-compose
docker-compose run --rm trends-story

# Using docker directly
docker run --rm -v $(pwd):/app/trends-story trends-story:latest
```

The container will execute [`creating-stories.py`](creating-stories.py), perform git operations, and exit.

---

## 🔧 Docker Commands Reference

### Building the Image

```bash
# Build with docker-compose
docker-compose build

# Build with docker directly
docker build -t trends-story:latest .

# Build without cache (force rebuild)
docker-compose build --no-cache
docker build --no-cache -t trends-story:latest .
```

### Running Containers

```bash
# Scheduled mode - background
docker-compose up -d

# Scheduled mode - foreground (see live output)
docker-compose up

# Immediate mode - one-time execution
docker-compose run --rm trends-story

# With custom volume mount
docker run -d --name trends-story \
  -v /path/to/your/repo:/app/trends-story \
  trends-story:latest
```

### Viewing Logs

```bash
# Follow logs in real-time
docker-compose logs -f

# Last 50 lines
docker-compose logs --tail=50

# Logs from specific timestamp
docker-compose logs --since="2025-01-01T00:00:00"

# Application logs inside container
docker-compose exec trends-story cat /var/log/trends-story/cron.log

# Daily rotating logs
docker-compose exec trends-story ls -lh /app/trends-story/logs/
```

### Container Management

```bash
# Stop container
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Restart container
docker-compose restart

# Access container shell
docker-compose exec trends-story bash

# Execute command in container
docker-compose exec trends-story python3 --version

# View running containers
docker-compose ps

# Remove stopped container
docker rm trends-story-automation
```

### Health Check Status

```bash
# Check health status
docker inspect trends-story-automation | grep -A 10 "Health"

# View health check logs
docker inspect trends-story-automation --format='{{json .State.Health}}' | jq
```

---

## 🏗️ How It Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Container                         │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  entrypoint.sh                                        │ │
│  │  ├─ Validate config.yaml                             │ │
│  │  ├─ Check run_mode                                   │ │
│  │  ├─ Configure git credentials                        │ │
│  │  └─ Branch to mode:                                  │ │
│  │     ├─ immediate → run_and_sync.py → exit            │ │
│  │     └─ scheduled → setup cron → keep running         │ │
│  └───────────────────────────────────────────────────────┘ │
│                             │                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  run_and_sync.py (Wrapper Script)                    │ │
│  │  ├─ Create lockfile (.run.lock)                      │ │
│  │  ├─ Execute creating-stories.py                      │ │
│  │  ├─ Capture & log output                             │ │
│  │  └─ If successful:                                   │ │
│  │     ├─ git checkout .                                │ │
│  │     ├─ git add .                                     │ │
│  │     ├─ git commit                                    │ │
│  │     ├─ git fetch & rebase                            │ │
│  │     ├─ git push                                      │ │
│  │     └─ Update .last_run timestamp                    │ │
│  └───────────────────────────────────────────────────────┘ │
│                             │                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  creating-stories.py (Main Application)              │ │
│  │  ├─ Fetch trending topics                            │ │
│  │  ├─ Generate stories                                 │ │
│  │  ├─ Create images                                    │ │
│  │  └─ Save to images/ directory                        │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
                 ┌─────────────────────┐
                 │  GitHub Repository  │
                 │  - Updated images   │
                 │  - Commit history   │
                 └─────────────────────┘
```

### Execution Workflow

1. **Container Starts** → [`entrypoint.sh`](entrypoint.sh:1) executes
2. **Configuration Validation** → Checks [`config.yaml`](config.yaml) exists and is valid
3. **Mode Detection** → Reads `run_mode` from config
4. **For Scheduled Mode:**
   - Sets up cron job with specified schedule
   - Starts cronie daemon in foreground
   - Container keeps running indefinitely
5. **For Immediate Mode:**
   - Executes [`run_and_sync.py`](run_and_sync.py:1) immediately
   - Container exits after completion
6. **Script Execution** ([`run_and_sync.py`](run_and_sync.py:1)):
   - Creates lockfile to prevent concurrent runs
   - Executes [`creating-stories.py`](creating-stories.py)
   - Logs all output to console and file
7. **Git Operations** (if script succeeds):
   - `git checkout .` - Clean workspace
   - `git add .` - Stage all changes
   - `git commit -m "Update news YYYYMMDD"` - Create commit
   - `git fetch origin main` - Fetch remote changes
   - `git rebase origin/main` - Rebase on latest
   - `git push origin main` - Push to GitHub
8. **Timestamp Update** → Updates [`.last_run`](.last_run) for health checks
9. **Cleanup** → Removes lockfile

---

## 📁 File Structure

```
trends-story/
├── Dockerfile                 # Container image definition
├── docker-compose.yml         # Docker Compose orchestration
├── entrypoint.sh             # Container startup script
├── run_and_sync.py           # Wrapper script for execution + git sync
├── creating-stories.py       # Main application script
├── config.yaml               # Your configuration (DO NOT COMMIT!)
├── config.example.yaml       # Configuration template
├── .gitignore               # Git ignore rules
├── DOCKER_README.md         # This documentation
├── logs/                    # Application logs (rotating)
│   └── run_YYYYMMDD.log    # Daily log files
├── images/                  # Generated images
│   └── YYYY/MM/DD/         # Date-organized images
└── .last_run               # Health check timestamp file
```

### File Purpose

| File | Purpose |
|------|---------|
| [`Dockerfile`](Dockerfile:1) | Defines the container image with Fedora base, Python, git, and cronie |
| [`docker-compose.yml`](docker-compose.yml:1) | Simplifies deployment with predefined configuration |
| [`entrypoint.sh`](entrypoint.sh:1) | Container entry point; validates config and manages execution modes |
| [`run_and_sync.py`](run_and_sync.py:1) | Wrapper script that executes main script and handles git operations |
| [`creating-stories.py`](creating-stories.py) | Main application logic for story generation |
| [`config.yaml`](config.yaml) | **Your secrets** - never commit this file! |
| [`config.example.yaml`](config.example.yaml:1) | Template showing required configuration structure |
| [`.gitignore`](.gitignore) | Ensures sensitive files aren't committed |

---

## 📊 Logging

### Log Locations

1. **Container stdout/stderr** - Docker logs
2. **Rotating log files** - `logs/run_YYYYMMDD.log`
3. **Cron logs** - `/var/log/trends-story/cron.log` (inside container)

### Log Rotation Policy

- **Max file size**: 10 MB per log file
- **Retention**: 7 days (7 backup files)
- **Format**: `[YYYY-MM-DD HH:MM:SS] [LEVEL] message`

### Viewing Logs

```bash
# Docker logs (all container output)
docker-compose logs -f

# Application logs (outside container)
cat logs/run_$(date +%Y%m%d).log

# Cron logs (inside container)
docker-compose exec trends-story cat /var/log/trends-story/cron.log

# All recent logs
docker-compose exec trends-story ls -lht /app/trends-story/logs/
```

### Log Levels

- **INFO** - Normal operations, status updates
- **WARNING** - Non-critical issues, retries
- **ERROR** - Failures requiring attention
- **SUCCESS** - Successful completion of operations

---

## 🔍 Troubleshooting

### Container Exits Immediately

**Symptom**: Container starts then stops right away

**Check**:
```bash
docker-compose logs
```

**Common Causes**:
1. **Missing [`config.yaml`](config.yaml)**
   - Solution: Copy and configure from [`config.example.yaml`](config.example.yaml:1)

2. **Invalid run_mode**
   - Solution: Ensure `run_mode` is exactly `"scheduled"` or `"immediate"`

3. **Invalid cron schedule**
   - Solution: Verify cron syntax (5 fields: `minute hour day month weekday`)

### Authentication Failures

**Symptom**: `fatal: Authentication failed` or `403 Forbidden`

**Solutions**:

1. **Check token validity**:
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
   ```

2. **Verify token permissions**:
   - Go to [GitHub Settings → Tokens](https://github.com/settings/tokens)
   - Ensure `repo` or `public_repo` scope is enabled

3. **Update token in [`config.yaml`](config.yaml)**:
   ```yaml
   git_token: "ghp_your_new_token_here"
   ```

4. **Rebuild container**:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

### Script Execution Failures

**Symptom**: Script runs but fails or produces errors

**Check logs**:
```bash
docker-compose logs | grep -A 20 "\[SCRIPT\]"
```

**Common Issues**:

1. **Missing Python dependencies**:
   - Add to [`Dockerfile`](Dockerfile:64):
     ```dockerfile
     RUN pip3 install --no-cache-dir \
         serpapi \
         websockets \
         websocket-client \
         pyyaml \
         your-missing-package
     ```

2. **File permissions**:
   ```bash
   chmod +x creating-stories.py
   ```

3. **Python path issues**:
   - Check imports in [`creating-stories.py`](creating-stories.py)

### Git Conflicts

**Symptom**: `Rebase failed - conflicts detected`

**This requires manual intervention**:

```bash
# Access container
docker-compose exec trends-story bash

# Check git status
cd /app/trends-story
git status

# Resolve conflicts manually
git rebase --abort  # Or resolve and continue
git reset --hard origin/main  # Discard local changes

# Exit and restart
exit
docker-compose restart
```

**Prevention**: Avoid modifying files both locally and via automation

### Lock File Issues

**Symptom**: `Lockfile exists and is recent` messages

**Automatic cleanup**: Stale locks (>30 minutes) are auto-removed

**Manual cleanup**:
```bash
# Remove lock file
rm .run.lock

# Or inside container
docker-compose exec trends-story rm /app/trends-story/.run.lock
```

### Health Check Failures

**Symptom**: Container marked as `unhealthy`

**Check health status**:
```bash
docker inspect trends-story-automation | grep -A 10 Health
```

**Common causes**:

1. **[`.last_run`](.last_run) file too old** (>24 hours)
   - Check if cron is running:
     ```bash
     docker-compose exec trends-story ps aux | grep crond
     ```

2. **Script hasn't run yet** (container just started)
   - Wait for first scheduled execution or run immediate mode

3. **Script keeps failing**
   - Check logs for errors:
     ```bash
     docker-compose logs --tail=100
     ```

---

## 🚀 Advanced Usage

### Custom Cron Schedules

Beyond basic examples, you can create complex schedules:

```yaml
# Business hours only (9 AM - 5 PM, Mon-Fri)
cron_schedule: "0 9-17 * * 1-5"

# Every 15 minutes during market hours
cron_schedule: "*/15 9-16 * * 1-5"

# First day of every month at midnight
cron_schedule: "0 0 1 * *"

# Every Sunday at 2 AM (maintenance window)
cron_schedule: "0 2 * * 0"
```

### Running Multiple Instances

⚠️ **Not recommended** due to git conflicts, but possible:

1. Use separate branches for each instance
2. Modify cron schedules to avoid overlap
3. Consider separate repositories instead

**Example**:
```yaml
# Instance 1: config_instance1.yaml
cron_schedule: "0 */6 * * *"  # Every 6 hours

# Instance 2: config_instance2.yaml
cron_schedule: "30 */6 * * *"  # Every 6 hours, offset by 30 min
```

### Modifying the Execution Script

To test changes to [`creating-stories.py`](creating-stories.py):

```bash
# 1. Edit the script locally
nano creating-stories.py

# 2. Run in immediate mode (no rebuild needed, uses volume mount)
docker-compose run --rm trends-story

# 3. If successful, commit changes
git add creating-stories.py
git commit -m "Update story generation logic"
git push
```

### Environment Variable Overrides

Override config values with environment variables:

```yaml
# docker-compose.yml
services:
  trends-story:
    environment:
      - TZ=America/Los_Angeles  # Change timezone
      - PYTHONUNBUFFERED=1
      - GIT_TOKEN=${GIT_TOKEN}  # From .env file
```

Create `.env` file:
```bash
GIT_TOKEN=ghp_your_token_here
```

### Volume Mount Customization

Mount specific directories instead of entire repo:

```yaml
volumes:
  - ./config.yaml:/app/trends-story/config.yaml:ro  # Read-only config
  - ./logs:/app/trends-story/logs
  - ./images:/app/trends-story/images
  - ./creating-stories.py:/app/trends-story/creating-stories.py
```

---

## 📡 Monitoring

### Health Check Explanation

The container health check monitors script execution by checking the [`.last_run`](.last_run) timestamp:

- **Healthy**: File exists and is less than 24 hours old
- **Unhealthy**: File missing or older than 24 hours
- **Starting**: Grace period (30 seconds) after container start

**Health check command** (inside container):
```bash
test -f /app/trends-story/.last_run && \
  test $(find /app/trends-story/.last_run -mmin -1440 | wc -l) -gt 0
```

### Exit Codes

The [`run_and_sync.py`](run_and_sync.py:29) script uses these exit codes:

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | All operations completed successfully |
| `1` | Config Error | Missing or invalid configuration |
| `2` | Script Failure | [`creating-stories.py`](creating-stories.py) failed |
| `3` | Git Failure | Git operations failed (commit/push) |

### Setting Up Alerts

**Using Docker Events**:
```bash
# Monitor health status changes
docker events --filter event=health_status

# Send to monitoring system
docker events --filter event=health_status | \
  while read event; do
    curl -X POST https://your-monitoring-service.com/alert \
      -d "$event"
  done
```

**Log-based Monitoring**:
```bash
# Watch for ERROR level logs
docker-compose logs -f | grep -i error

# Send email on failure
docker-compose logs --tail=50 | grep -i "ERROR" && \
  echo "Container error detected" | mail -s "Alert" you@example.com
```

**Third-party Tools**:
- [Portainer](https://www.portainer.io/) - Docker management UI
- [Watchtower](https://containrrr.dev/watchtower/) - Automatic updates
- [Prometheus](https://prometheus.io/) + [cAdvisor](https://github.com/google/cadvisor) - Metrics collection

---

## 🔐 Security Considerations

### Token Security

⚠️ **Critical Security Rules**:

1. **Never commit [`config.yaml`](config.yaml)** - It contains your token!
   - Already in [`.gitignore`](.gitignore), but verify:
     ```bash
     git status --ignored | grep config.yaml
     ```

2. **Use tokens with minimal permissions**:
   - Public repos: Only `public_repo` scope
   - Private repos: Only `repo` scope (not all admin scopes)

3. **Rotate tokens regularly**:
   - Generate new token every 90 days
   - Revoke old tokens after updating

4. **Monitor token usage**:
   - Check [GitHub Security Log](https://github.com/settings/security-log)
   - Review [Authorized OAuth Apps](https://github.com/settings/applications)

### Container Security

**Current Setup** (runs as root):
```dockerfile
# No USER directive, runs as root (UID 0)
```

**Production Recommendation** (run as non-root):
```dockerfile
# Add to Dockerfile
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app/trends-story
USER appuser
```

### Network Security

**Restrict network access** (if needed):
```yaml
# docker-compose.yml
services:
  trends-story:
    networks:
      - trends-net
    # Only allow GitHub
    extra_hosts:
      - "github.com:140.82.114.4"

networks:
  trends-net:
    driver: bridge
```

### Secret Management Alternatives

Instead of [`config.yaml`](config.yaml), consider:

**1. Docker Secrets** (Swarm mode):
```bash
echo "ghp_your_token" | docker secret create git_token -
```

**2. Environment Variables**:
```bash
export GIT_TOKEN="ghp_your_token"
docker-compose up -d
```

**3. External Secret Managers**:
- [HashiCorp Vault](https://www.vaultproject.io/)
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [Azure Key Vault](https://azure.microsoft.com/en-us/services/key-vault/)

---

## 🛠️ Maintenance

### Updating the Container

**When code changes**:
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose up -d --build

# Verify new version
docker-compose logs --tail=50
```

**When dependencies change**:
```bash
# Edit Dockerfile to add packages
nano Dockerfile

# Rebuild without cache
docker-compose build --no-cache

# Restart
docker-compose up -d
```

### Rebuilding After Code Changes

```bash
# Quick rebuild (uses cache)
docker-compose up -d --build

# Full rebuild (no cache)
docker-compose build --no-cache
docker-compose up -d

# Force recreate containers
docker-compose up -d --force-recreate
```

### Log Cleanup

**Automatic**: Logs rotate after 7 days or 10 MB

**Manual cleanup**:
```bash
# Remove old log files
find logs/ -name "*.log" -mtime +30 -delete

# Clear Docker logs
docker-compose down
docker system prune -a --volumes

# Remove specific log file
rm logs/run_20250101.log
```

### Backup Recommendations

**What to backup**:
1. [`config.yaml`](config.yaml) (securely!)
2. `logs/` directory (optional)
3. `images/` directory (if not in Git)

**Backup script**:
```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backups/trends-story"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" config.yaml
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" logs/

# Encrypt config backup
gpg -c "$BACKUP_DIR/config_$DATE.tar.gz"
rm "$BACKUP_DIR/config_$DATE.tar.gz"
```

---

## 🧪 Development & Testing

### Local Testing Workflow

1. **Make changes to scripts locally**
2. **Test in immediate mode**:
   ```bash
   # Update config.yaml
   sed -i 's/run_mode: "scheduled"/run_mode: "immediate"/' config.yaml
   
   # Run once
   docker-compose run --rm trends-story
   ```

3. **Check logs**:
   ```bash
   cat logs/run_$(date +%Y%m%d).log
   ```

4. **If successful, switch to scheduled**:
   ```bash
   sed -i 's/run_mode: "immediate"/run_mode: "scheduled"/' config.yaml
   docker-compose up -d
   ```

### Testing Changes Before Deployment

**Test script changes without Docker**:
```bash
# Activate virtual environment (if you have one)
source venv/bin/activate

# Run directly
python3 creating-stories.py

# Run wrapper
python3 run_and_sync.py
```

**Test Docker configuration**:
```bash
# Validate docker-compose.yml
docker-compose config

# Check Dockerfile syntax
docker build --dry-run -t trends-story:test .

# Run temporary container
docker run --rm -it \
  -v $(pwd):/app/trends-story \
  trends-story:latest bash
```

### Debugging Tips

**1. Access running container**:
```bash
docker-compose exec trends-story bash
```

**2. Check environment**:
```bash
docker-compose exec trends-story env | sort
```

**3. Verify cron setup**:
```bash
docker-compose exec trends-story crontab -l
```

**4. Test script manually**:
```bash
docker-compose exec trends-story python3 /app/trends-story/creating-stories.py
```

**5. Check git configuration**:
```bash
docker-compose exec trends-story git config --list
```

**6. Monitor in real-time**:
```bash
# Terminal 1: Watch logs
docker-compose logs -f

# Terminal 2: Monitor processes
watch -n 5 'docker-compose exec trends-story ps aux'

# Terminal 3: Check files
watch -n 10 'docker-compose exec trends-story ls -lht /app/trends-story/images/'
```

---

## ❓ FAQ

### How do I change the schedule?

Edit the `cron_schedule` in [`config.yaml`](config.yaml) and restart:
```bash
nano config.yaml  # Change cron_schedule
docker-compose restart
```

### Can I run this outside Docker?

Yes! Docker is optional. Install dependencies and run:
```bash
pip3 install serpapi websockets websocket-client pyyaml
python3 run_and_sync.py
```

For scheduling, add to your system crontab:
```bash
crontab -e
# Add: 0 5,16 * * * cd /path/to/trends-story && python3 run_and_sync.py
```

### What happens if the script fails?

1. **Script execution fails** → Git operations skipped, exit code 2
2. **Git operations fail** → Changes not pushed, exit code 3
3. **Next scheduled run** → Tries again from scratch
4. **Lockfile** → Prevents concurrent executions

Check logs:
```bash
docker-compose logs | grep ERROR
```

### How do I update the Python script?

The script is mounted as a volume, so changes take effect immediately:

```bash
# Edit locally
nano creating-stories.py

# Test (no rebuild needed)
docker-compose run --rm trends-story

# Commit if successful
git add creating-stories.py
git commit -m "Update script"
```

### How do I check if it's working?

**1. Check container status**:
```bash
docker-compose ps
```

**2. Check health**:
```bash
docker inspect trends-story-automation --format='{{.State.Health.Status}}'
```

**3. Check recent execution**:
```bash
cat .last_run
```

**4. Check logs**:
```bash
docker-compose logs --tail=50 | grep -i success
```

**5. Check generated images**:
```bash
ls -lht images/ | head -20
```

### How often should I rotate my GitHub token?

**Recommended**: Every 90 days

**Best practice**:
1. Set token expiration when creating
2. Calendar reminder 1 week before expiration
3. Generate new token
4. Update [`config.yaml`](config.yaml)
5. Restart container
6. Revoke old token

### Can I use this for multiple GitHub repos?

Not directly. Alternatives:

1. **Run separate containers** with different working directories
2. **Modify scripts** to handle multiple repos
3. **Clone pattern** - duplicate entire setup for each repo

### What timezone does the container use?

**Default**: America/New_York (EST/EDT)

**Change timezone**:
```yaml
# docker-compose.yml
environment:
  - TZ=America/Los_Angeles  # Or any valid timezone
```

**Available timezones**:
```bash
docker-compose exec trends-story ls /usr/share/zoneinfo/
```

### How much disk space will this use?

**Approximate usage**:
- Container image: ~500 MB
- Logs (7 days): ~70 MB (10 MB × 7)
- Images: Varies by script output

**Monitor usage**:
```bash
# Container size
docker-compose images

# Volume size
du -sh logs/ images/

# Total Docker usage
docker system df
```

---

## 📚 Additional Resources

### Documentation Links

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Cron Expression Guide](https://crontab.guru/)
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [Fedora Container Documentation](https://docs.fedoraproject.org/en-US/containers/)

### Related Files

- [Main README](README.md) - Project documentation
- [`Dockerfile`](Dockerfile:1) - Container definition
- [`docker-compose.yml`](docker-compose.yml:1) - Orchestration config
- [`entrypoint.sh`](entrypoint.sh:1) - Startup script
- [`run_and_sync.py`](run_and_sync.py:1) - Wrapper script
- [`config.example.yaml`](config.example.yaml:1) - Configuration template

---

## 📄 License

This Docker setup is part of the trends-story project. Refer to the main repository for license information.

---

## 🤝 Support

If you encounter issues:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review [FAQ](#-faq)
3. Check container logs: `docker-compose logs`
4. Open an issue on GitHub with logs and configuration (sanitize tokens!)

---

**Last Updated**: November 2025  
**Container Version**: 1.0.0  
**Maintainer**: trends-story-team
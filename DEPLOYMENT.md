# Deployment Guide for Trends Story

## Prerequisites

- Docker and Docker Compose installed on your server
- Git repository cloned to your deployment environment
- GitHub Personal Access Token with repository access

## Initial Setup

### 1. Create Configuration File

The `config.yaml` file contains sensitive credentials and is not included in the repository. You must create it manually:

```bash
# Navigate to the repository directory
cd /path/to/trends-story

# Copy the example configuration
cp config.example.yaml config.yaml

# Edit the configuration file
nano config.yaml  # or use your preferred editor
```

**Required configurations in config.yaml:**
- `git_token`: Your GitHub Personal Access Token (get it from https://github.com/settings/tokens)
- `run_mode`: Set to `"scheduled"` for continuous operation or `"immediate"` for one-time execution
- `cron_schedule`: When to run (only needed if run_mode is "scheduled")

Example:
```yaml
git_token: "ghp_YourActualTokenHere"
run_mode: "scheduled"
cron_schedule: "0 5,16 * * *"  # Runs at 5 AM and 4 PM daily
```

### 2. Verify File Permissions

Ensure the configuration file exists and is readable:

```bash
ls -la config.yaml
# Should show: -rw-r--r-- 1 user user ... config.yaml
```

### 3. Build the Docker Image

```bash
docker-compose build
```

### 4. Start the Container

For scheduled/continuous operation:
```bash
docker-compose up -d
```

For immediate/one-time execution:
```bash
# First, set run_mode to "immediate" in config.yaml
# Then run:
docker-compose run --rm trends-story
```

## Verification

### Check Container Status

```bash
docker-compose ps
```

Expected output for scheduled mode:
```
NAME                      STATUS                 PORTS
trends-story-automation   Up X minutes (healthy)
```

### View Logs

```bash
# Live log streaming
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# View cron logs inside container
docker-compose exec trends-story cat /var/log/trends-story/cron.log
```

### Verify Configuration Loaded

```bash
docker-compose logs | grep "Config Location"
```

You should see:
```
[YYYY-MM-DD HH:MM:SS] Config Location: /app/trends-story/config.yaml
```

## Troubleshooting

### Error: "Config file not found at /app/trends-story/config.yaml"

**Cause:** The `config.yaml` file doesn't exist on the host machine.

**Solution:**
```bash
# Ensure you're in the repository directory
pwd  # Should show /path/to/trends-story

# Check if config.yaml exists
ls -la config.yaml

# If not, create it from the example
cp config.example.yaml config.yaml

# Edit and add your credentials
nano config.yaml

# Restart the container
docker-compose down
docker-compose up -d
```

### Error: "git_token is missing or empty in config.yaml"

**Cause:** The config.yaml file exists but is missing the git_token.

**Solution:**
```bash
# Edit config.yaml and add your GitHub token
nano config.yaml

# Restart the container
docker-compose restart
```

### Container Starts but Nothing Happens

**Possible causes:**
1. Wrong run_mode setting
2. Invalid cron_schedule format
3. Script execution errors

**Solution:**
```bash
# Check the logs for errors
docker-compose logs -f

# Verify config.yaml settings
cat config.yaml

# Test in immediate mode
# Edit config.yaml and set: run_mode: "immediate"
docker-compose down
docker-compose up
```

## Production Deployment Checklist

- [ ] Clone repository to production server
- [ ] Create `config.yaml` from `config.example.yaml`
- [ ] Add GitHub Personal Access Token to `config.yaml`
- [ ] Set appropriate `run_mode` (usually "scheduled")
- [ ] Configure `cron_schedule` for desired execution times
- [ ] Adjust timezone in `docker-compose.yml` if needed
- [ ] Run `docker-compose build`
- [ ] Start with `docker-compose up -d`
- [ ] Verify container health: `docker-compose ps`
- [ ] Check logs: `docker-compose logs -f`
- [ ] Verify first execution completes successfully
- [ ] Set up monitoring/alerting (optional)

## Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d

# Verify
docker-compose logs -f
```

## Security Notes

1. **Never commit config.yaml** - It's already in `.gitignore`
2. **Protect your GitHub token** - Treat it like a password
3. **Use read-only mount** - The docker-compose.yml mounts config.yaml as read-only
4. **Rotate tokens regularly** - Generate new tokens periodically
5. **Limit token permissions** - Only grant necessary repository access

## Maintenance

### View Generated Content

Images and logs are stored in the repository directories:
```bash
ls -la images/
ls -la logs/
```

### Manual Execution

To run the script manually inside the container:
```bash
docker-compose exec trends-story python3 /app/trends-story/run_and_sync.py
```

### Stop the Container

```bash
docker-compose down
```

### Complete Cleanup

```bash
# Stop and remove container
docker-compose down

# Remove image
docker rmi trends-story:latest

# Clean up generated files (optional)
rm -rf logs/ images/
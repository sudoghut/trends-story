#!/bin/bash
set -e

# Color codes for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function with timestamp
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log_error() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${RED}ERROR${NC}: $1" >&2
}

log_success() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${GREEN}SUCCESS${NC}: $1"
}

log_warning() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${YELLOW}WARNING${NC}: $1"
}

# Initial configuration - will be updated after reading config
CONFIG_FILE="/app/trends-story/config.yaml"

# Signal handling for graceful shutdown
cleanup() {
    log "Received shutdown signal, cleaning up..."
    if [ -f /var/run/crond.pid ]; then
        kill $(cat /var/run/crond.pid) 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGTERM SIGINT

# Get base directory from config file
get_base_dir() {
    python3 << 'EOF'
import yaml
import sys
import os

config_paths = [
    "/app/trends-story/config.yaml",
    "./config.yaml",
    os.path.join(os.getcwd(), "config.yaml")
]

for config_path in config_paths:
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            base_dir = config.get('base_dir', '/app/trends-story')
            print(base_dir)
            sys.exit(0)
        except Exception:
            continue

# Default fallback
print('/app/trends-story')
EOF
}

# Initialize paths based on config
initialize_paths() {
    local base_dir=$(get_base_dir)
    
    # Update global variables
    BASE_DIR="$base_dir"
    CONFIG_FILE="$base_dir/config.yaml"
    WRAPPER_SCRIPT="$base_dir/run_and_sync.py"
    LOGS_DIR="$base_dir/logs"
    LOCK_DIR="$base_dir"
    
    log "Initialized with base directory: $BASE_DIR"
}

# Clean up stale lock files (older than 30 minutes)
cleanup_stale_locks() {
    log "Cleaning up stale lock files..."
    find "$LOCK_DIR" -name "*.lock" -type f -mmin +30 -delete 2>/dev/null || true
}

# Validate Python environment
validate_python_env() {
    log "Validating Python environment..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is not installed"
        exit 1
    fi
    
    # Check for required Python packages
    python3 -c "import yaml" 2>/dev/null || {
        log_error "PyYAML is not installed"
        exit 1
    }
    
    log_success "Python environment validated"
}

# Validate configuration file
validate_config() {
    log "Validating configuration file..."
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Config file not found at $CONFIG_FILE"
        exit 1
    fi
    
    # Use Python to validate YAML and extract values
    python3 << EOF
import sys
import yaml

try:
    with open('${CONFIG_FILE}', 'r') as f:
        config = yaml.safe_load(f)
    
    # Check required fields
    if 'git_token' not in config or not config['git_token']:
        print("ERROR: 'git_token' is missing or empty in config.yaml", file=sys.stderr)
        sys.exit(1)
    
    if 'run_mode' not in config or not config['run_mode']:
        print("ERROR: 'run_mode' is missing or empty in config.yaml", file=sys.stderr)
        sys.exit(1)
    
    # Validate run_mode
    if config['run_mode'] not in ['scheduled', 'immediate']:
        print(f"ERROR: 'run_mode' must be 'scheduled' or 'immediate', got '{config['run_mode']}'", file=sys.stderr)
        sys.exit(1)
    
    # Check cron_schedule if in scheduled mode
    if config['run_mode'] == 'scheduled':
        if 'cron_schedule' not in config or not config['cron_schedule']:
            print("ERROR: 'cron_schedule' is required when run_mode is 'scheduled'", file=sys.stderr)
            sys.exit(1)
        
        # Basic cron format validation (5 or 6 fields)
        cron_fields = config['cron_schedule'].strip().split()
        if len(cron_fields) not in [5, 6]:
            print(f"ERROR: Invalid cron format. Expected 5 or 6 fields, got {len(cron_fields)}", file=sys.stderr)
            print(f"       Cron schedule: {config['cron_schedule']}", file=sys.stderr)
            sys.exit(1)
    
    print("SUCCESS")
    
except yaml.YAMLError as e:
    print(f"ERROR: Failed to parse YAML file: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Validation failed: {e}", file=sys.stderr)
    sys.exit(1)
EOF
    
    if [ $? -ne 0 ]; then
        exit 1
    fi
    
    log_success "Configuration validated"
}

# Get configuration value using Python
get_config_value() {
    local key=$1
    python3 << EOF
import yaml
with open('${CONFIG_FILE}', 'r') as f:
    config = yaml.safe_load(f)
print(config.get('${key}', ''))
EOF
}

# Configure git
configure_git() {
    log "Configuring git..."
    
    local git_token=$(get_config_value "git_token")
    local git_user=$(get_config_value "git_user" || echo "Trends Story Bot")
    local git_email=$(get_config_value "git_email" || echo "bot@trends-story.local")
    
    git config --global user.name "$git_user"
    git config --global user.email "$git_email"
    
    # Configure credential helper to use token
    git config --global credential.helper store
    
    log_success "Git configured with user: $git_user <$git_email>"
}

# Display startup summary
display_startup_summary() {
    local run_mode=$(get_config_value "run_mode")
    local timezone=$(get_config_value "timezone" || echo "UTC")
    
    log "=================================="
    log "   Trends Story Container Start"
    log "=================================="
    log "Base Directory: $BASE_DIR"
    log "Run Mode: $run_mode"
    log "Config Location: $CONFIG_FILE"
    log "Timezone: $timezone"
    
    run_mode=${run_mode//\"/}
    run_mode=${run_mode//\'/}

    if [ "$run_mode" == "scheduled" ]; then
        local cron_schedule=$(get_config_value "cron_schedule")
        log "Cron Schedule: $cron_schedule"
    fi
    
    log "Logs Directory: $LOGS_DIR"
    log "=================================="
}

# Run in immediate mode
run_immediate_mode() {
    log "Starting in IMMEDIATE mode..."
    log "Executing wrapper script once..."
    
    if [ ! -f "$WRAPPER_SCRIPT" ]; then
        log_error "Wrapper script not found at $WRAPPER_SCRIPT"
        exit 1
    fi
    
    python3 "$WRAPPER_SCRIPT"
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_success "Wrapper script completed successfully"
    else
        log_error "Wrapper script failed with exit code $exit_code"
    fi
    
    exit $exit_code
}

# Run in scheduled mode
run_scheduled_mode() {
    log "Starting in SCHEDULED mode..."
    
    local cron_schedule=$(get_config_value "cron_schedule")
    
    if [ ! -f "$WRAPPER_SCRIPT" ]; then
        log_error "Wrapper script not found at $WRAPPER_SCRIPT"
        exit 1
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p "$LOGS_DIR"
    
    # Create cron job with full environment and output redirection
    log "Setting up cron job with schedule: $cron_schedule"
    
    # Get current environment variables to pass to cron
    local env_vars=""
    for var in $(printenv | grep -E '^(PATH|PYTHONPATH|HOME|USER|SHELL)=' | sed 's/=.*//'); do
        env_vars="$env_vars$var=$(printenv $var)\n"
    done
    
    # Create crontab entry that redirects output to stdout/stderr
    (
        echo -e "$env_vars"
        echo "$cron_schedule cd $BASE_DIR && python3 $WRAPPER_SCRIPT >> /proc/1/fd/1 2>> /proc/1/fd/2"
    ) | crontab -
    
    log_success "Cron job installed"
    
    # Display crontab for verification
    log "Installed crontab:"
    crontab -l | grep -v "^[A-Z]" | grep -v "^$"
    
    # Start cronie daemon in foreground
    log "Starting cronie daemon..."
    exec crond -f -l 2
}

# Main execution
main() {
    log "Starting Trends Story entrypoint script..."
    
    # Initialize paths from config
    initialize_paths
    
    # Cleanup stale locks
    cleanup_stale_locks
    
    # Validate Python environment
    validate_python_env
    
    # Validate configuration
    validate_config
    
    # Configure git
    configure_git
    
    # Display startup summary
    display_startup_summary
    
    # Get run mode and execute accordingly
    local run_mode=$(get_config_value "run_mode")
    
    case "$run_mode" in
        immediate)
            run_immediate_mode
            ;;
        scheduled)
            run_scheduled_mode
            ;;
        *)
            log_error "Unknown run_mode: $run_mode"
            exit 1
            ;;
    esac
}

# Execute main function
main
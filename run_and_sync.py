#!/usr/bin/env python3
"""
Wrapper script for executing creating-stories.py with git operations.
Handles lockfile management, script execution, and automated git sync.
"""

import subprocess
import sys
import os
import datetime
import time
import yaml
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import json

# Constants
BASE_DIR = Path("/app/trends-story")
LOCKFILE = BASE_DIR / ".run.lock"
LAST_RUN_FILE = BASE_DIR / ".last_run"
CONFIG_FILE = BASE_DIR / "config.yaml"
LOG_DIR = BASE_DIR / "logs"
SCRIPT_PATH = BASE_DIR / "creating-stories.py"
LOCKFILE_STALE_MINUTES = 30
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds

# Exit codes
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_SCRIPT_FAILURE = 2
EXIT_GIT_FAILURE = 3


def setup_logging():
    """Setup dual logging to stdout and rotating file."""
    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get current date in NY timezone
    ny_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5)))
    log_file = LOG_DIR / f"run_{ny_date.strftime('%Y%m%d')}.log"
    
    # Create logger
    logger = logging.getLogger('run_and_sync')
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Format for logs
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (keep 7 days)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=7
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def check_lockfile(logger):
    """Check if lockfile exists and handle stale locks."""
    if LOCKFILE.exists():
        # Check if lockfile is stale
        lock_age = time.time() - LOCKFILE.stat().st_mtime
        lock_age_minutes = lock_age / 60
        
        if lock_age_minutes > LOCKFILE_STALE_MINUTES:
            logger.warning(f"Lockfile is stale ({lock_age_minutes:.1f} minutes old). Removing.")
            LOCKFILE.unlink()
            return True
        else:
            logger.error(f"Lockfile exists and is recent ({lock_age_minutes:.1f} minutes old). Another instance may be running.")
            return False
    return True


def create_lockfile(logger):
    """Create lockfile to prevent concurrent runs."""
    try:
        LOCKFILE.parent.mkdir(parents=True, exist_ok=True)
        LOCKFILE.write_text(str(os.getpid()))
        logger.info(f"Created lockfile: {LOCKFILE}")
        return True
    except Exception as e:
        logger.error(f"Failed to create lockfile: {e}")
        return False


def remove_lockfile(logger):
    """Remove lockfile."""
    try:
        if LOCKFILE.exists():
            LOCKFILE.unlink()
            logger.info("Removed lockfile")
    except Exception as e:
        logger.error(f"Failed to remove lockfile: {e}")


def load_config(logger):
    """Load configuration from config.yaml."""
    try:
        if not CONFIG_FILE.exists():
            logger.error(f"Configuration file not found: {CONFIG_FILE}")
            return None
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Extract required fields
        git_token = config.get('git_token')
        if not git_token:
            logger.error("git_token not found in configuration")
            return None
        
        # Extract optional fields with defaults
        git_user_name = config.get('git_user_name', 'Trends Story Bot')
        git_user_email = config.get('git_user_email', 'bot@trends-story.local')
        
        logger.info("Configuration loaded successfully")
        return {
            'git_token': git_token,
            'git_user_name': git_user_name,
            'git_user_email': git_user_email
        }
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def execute_script(logger):
    """Execute creating-stories.py and capture output."""
    logger.info("=" * 60)
    logger.info("Starting creating-stories.py execution")
    logger.info("=" * 60)
    
    start_time = time.time()
    start_dt = datetime.datetime.now()
    logger.info(f"Execution start time: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Execute the script
        process = subprocess.Popen(
            [sys.executable, str(SCRIPT_PATH)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=str(BASE_DIR)
        )
        
        # Stream output to logs
        for line in process.stdout:
            logger.info(f"[SCRIPT] {line.rstrip()}")
        
        # Wait for process to complete
        return_code = process.wait()
        
        end_time = time.time()
        end_dt = datetime.datetime.now()
        duration = end_time - start_time
        
        logger.info(f"Execution end time: {end_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Execution duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        
        if return_code == 0:
            logger.info("Script execution completed successfully")
            return True
        else:
            logger.error(f"Script execution failed with return code: {return_code}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to execute script: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_git_command(command, logger, cwd=None, retry=False):
    """Run a git command with optional retry logic."""
    max_attempts = MAX_RETRIES if retry else 1
    
    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.info(f"Retry attempt {attempt + 1}/{max_attempts} after {delay}s delay")
                time.sleep(delay)
            
            logger.info(f"Running: {command}")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd or str(BASE_DIR),
                timeout=300  # 5 minute timeout
            )
            
            if result.stdout:
                logger.info(f"Output: {result.stdout.strip()}")
            if result.stderr:
                logger.warning(f"Stderr: {result.stderr.strip()}")
            
            if result.returncode == 0:
                return True
            else:
                logger.error(f"Command failed with return code: {result.returncode}")
                if attempt < max_attempts - 1 and retry:
                    continue
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Command timed out")
            if attempt < max_attempts - 1 and retry:
                continue
            return False
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            if attempt < max_attempts - 1 and retry:
                continue
            return False
    
    return False


def perform_git_operations(config, logger):
    """Perform git operations after successful script execution."""
    logger.info("=" * 60)
    logger.info("Starting git operations")
    logger.info("=" * 60)
    
    try:
        # Step 1: Clean workspace
        logger.info("Step 1: Cleaning workspace")
        if not run_git_command("git checkout .", logger):
            logger.error("Failed to clean workspace")
            return False
        
        # Step 2: Configure git user
        logger.info("Step 2: Configuring git user")
        if not run_git_command(f'git config user.name "{config["git_user_name"]}"', logger):
            logger.error("Failed to configure git user name")
            return False
        if not run_git_command(f'git config user.email "{config["git_user_email"]}"', logger):
            logger.error("Failed to configure git user email")
            return False
        
        # Step 3: Update remote URL with token
        logger.info("Step 3: Updating git remote URL")
        remote_url = f"https://{config['git_token']}@github.com/sudoghut/trends-story.git"
        if not run_git_command(f'git remote set-url origin {remote_url}', logger):
            logger.error("Failed to update remote URL")
            return False
        
        # Step 4: Stage changes (excluding runtime files that should be ignored)
        logger.info("Step 4: Staging changes")
        # First, ensure .run.lock and logs/ are not tracked if they exist
        subprocess.run("git rm --cached .run.lock 2>nul", shell=True, cwd=str(BASE_DIR))
        subprocess.run("git rm --cached -r logs/ 2>nul", shell=True, cwd=str(BASE_DIR))
        
        # Stage all changes except ignored files
        if not run_git_command("git add .", logger):
            logger.error("Failed to stage changes")
            return False
        
        # Step 5: Check if there are changes to commit
        logger.info("Step 5: Checking for changes")
        result = subprocess.run(
            "git diff --cached --quiet",
            shell=True,
            cwd=str(BASE_DIR)
        )
        
        if result.returncode != 0:
            # There are changes to commit
            # Get current date in NY timezone for commit message
            ny_tz = datetime.timezone(datetime.timedelta(hours=-5))
            ny_date = datetime.datetime.now(ny_tz)
            commit_msg = f"Update news {ny_date.strftime('%Y%m%d')}"
            
            logger.info(f"Step 6: Creating commit: {commit_msg}")
            if not run_git_command(f'git commit -m "{commit_msg}"', logger):
                logger.error("Failed to create commit")
                return False
        else:
            logger.info("No changes to commit, skipping commit step")
            return True
        
        # Step 7: Fetch and rebase
        logger.info("Step 7: Fetching from origin")
        if not run_git_command("git fetch origin main", logger, retry=True):
            logger.error("Failed to fetch from origin")
            return False
        
        logger.info("Step 8: Cleaning unstaged changes to ignored files before rebase")
        # Discard any local changes to .run.lock and logs/ to prevent rebase conflicts
        subprocess.run("git checkout -- .run.lock 2>nul", shell=True, cwd=str(BASE_DIR))
        subprocess.run("git checkout -- logs/ 2>nul", shell=True, cwd=str(BASE_DIR))
        subprocess.run("git clean -fd logs/ 2>nul", shell=True, cwd=str(BASE_DIR))
        
        logger.info("Step 9: Rebasing on origin/main")
        result = subprocess.run(
            "git rebase origin/main",
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR)
        )
        
        if result.returncode != 0:
            logger.error("Rebase failed - conflicts detected")
            logger.error(f"Rebase output: {result.stdout}")
            logger.error(f"Rebase errors: {result.stderr}")
            # Abort the rebase
            run_git_command("git rebase --abort", logger)
            return False
        
        logger.info("Rebase completed successfully")
        
        # Step 10: Push changes
        logger.info("Step 10: Pushing to origin/main")
        if not run_git_command("git push origin main", logger, retry=True):
            logger.error("Failed to push changes")
            return False
        
        logger.info("Git operations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Git operations failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def update_last_run_timestamp(logger):
    """Update the last run timestamp file."""
    try:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        LAST_RUN_FILE.write_text(timestamp)
        logger.info(f"Updated last run timestamp: {timestamp}")
        return True
    except Exception as e:
        logger.error(f"Failed to update last run timestamp: {e}")
        return False


def main():
    """Main execution function."""
    logger = setup_logging()
    exit_code = EXIT_SUCCESS
    
    try:
        logger.info("=" * 60)
        logger.info("Run and Sync Script Started")
        logger.info("=" * 60)
        
        # Check and create lockfile
        if not check_lockfile(logger):
            return EXIT_CONFIG_ERROR
        
        if not create_lockfile(logger):
            return EXIT_CONFIG_ERROR
        
        # Load configuration
        config = load_config(logger)
        if not config:
            return EXIT_CONFIG_ERROR
        
        # Execute the main script
        script_success = execute_script(logger)
        
        if not script_success:
            logger.error("Script execution failed - skipping git operations")
            exit_code = EXIT_SCRIPT_FAILURE
        else:
            # Perform git operations only if script succeeded
            git_success = perform_git_operations(config, logger)
            
            if not git_success:
                logger.error("Git operations failed")
                exit_code = EXIT_GIT_FAILURE
            else:
                # Update last run timestamp on complete success
                update_last_run_timestamp(logger)
                logger.info("All operations completed successfully")
        
    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user")
        exit_code = EXIT_SCRIPT_FAILURE
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        exit_code = EXIT_SCRIPT_FAILURE
    finally:
        # Always clean up lockfile
        remove_lockfile(logger)
        logger.info("=" * 60)
        logger.info(f"Run and Sync Script Finished (exit code: {exit_code})")
        logger.info("=" * 60)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
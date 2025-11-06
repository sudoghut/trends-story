#!/bin/bash

#############################################################################
# Docker Setup Validation Script for Trends Story
# This script validates that all prerequisites and configurations are 
# correctly set up before running the Docker container.
#############################################################################

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check symbols
CHECK_MARK="${GREEN}✓${NC}"
CROSS_MARK="${RED}✗${NC}"
WARNING_MARK="${YELLOW}⚠${NC}"

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Flags
VERBOSE=false
QUICK=false

# Log file
LOG_FILE="validation_log_$(date +%Y%m%d_%H%M%S).txt"

#############################################################################
# Helper Functions
#############################################################################

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${CHECK_MARK} $1"
    echo "[PASS] $1" >> "$LOG_FILE"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
}

print_error() {
    echo -e "${CROSS_MARK} $1"
    echo "[FAIL] $1" >> "$LOG_FILE"
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
}

print_warning() {
    echo -e "${WARNING_MARK} $1"
    echo "[WARN] $1" >> "$LOG_FILE"
    ((WARNING_CHECKS++))
}

print_info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "  ${BLUE}ℹ${NC} $1"
    fi
    echo "[INFO] $1" >> "$LOG_FILE"
}

print_help() {
    cat << EOF
Docker Setup Validation Script

USAGE:
    ./validate_setup.sh [OPTIONS]

OPTIONS:
    -h, --help      Show this help message
    -v, --verbose   Show detailed output for each check
    -q, --quick     Skip optional checks (GitHub token validation)

DESCRIPTION:
    This script validates your Docker setup before deployment by checking:
    - Docker and Docker Compose installation
    - Required files existence
    - Configuration file validity
    - File permissions
    - Git repository setup
    - GitHub token validation (optional)

EXIT CODES:
    0 - All critical checks passed
    1 - One or more critical checks failed

EXAMPLES:
    ./validate_setup.sh              # Run all checks
    ./validate_setup.sh --verbose    # Run with detailed output
    ./validate_setup.sh --quick      # Skip optional checks

EOF
}

#############################################################################
# Validation Functions
#############################################################################

check_docker_installed() {
    print_header "1. Checking Docker Prerequisites"
    
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker is installed: $DOCKER_VERSION"
    else
        print_error "Docker is not installed"
        echo -e "  ${RED}→${NC} Install Docker from: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    return 0
}

check_docker_running() {
    if docker info &> /dev/null; then
        print_success "Docker daemon is running"
    else
        print_error "Docker daemon is not running"
        echo -e "  ${RED}→${NC} Start Docker Desktop or run: sudo systemctl start docker"
        return 1
    fi
    
    return 0
}

check_docker_permissions() {
    if docker ps &> /dev/null; then
        print_success "User has permissions to run Docker commands"
    else
        print_error "User does not have permissions to run Docker commands"
        echo -e "  ${RED}→${NC} Add user to docker group: sudo usermod -aG docker \$USER"
        echo -e "  ${RED}→${NC} Then log out and back in, or run: newgrp docker"
        return 1
    fi
    
    return 0
}

check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
        print_success "Docker Compose is installed: $COMPOSE_VERSION"
    elif docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version)
        print_success "Docker Compose (plugin) is installed: $COMPOSE_VERSION"
    else
        print_error "Docker Compose is not installed"
        echo -e "  ${RED}→${NC} Install from: https://docs.docker.com/compose/install/"
        return 1
    fi
    
    return 0
}

check_required_files() {
    print_header "2. Checking Required Files"
    
    local files=(
        "Dockerfile"
        "docker-compose.yml"
        "entrypoint.sh"
        "run_and_sync.py"
        "creating-stories.py"
        "config.yaml"
    )
    
    local missing_files=()
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            print_success "Found: $file"
        else
            print_error "Missing: $file"
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        echo ""
        echo -e "${RED}Missing files detected:${NC}"
        for file in "${missing_files[@]}"; do
            if [ "$file" = "config.yaml" ]; then
                echo -e "  ${RED}→${NC} Copy config.example.yaml to config.yaml and configure it"
            else
                echo -e "  ${RED}→${NC} Ensure $file exists in the repository"
            fi
        done
        return 1
    fi
    
    return 0
}

check_config_yaml() {
    print_header "3. Validating Configuration File"
    
    if [ ! -f "config.yaml" ]; then
        print_error "config.yaml does not exist"
        echo -e "  ${RED}→${NC} Copy config.example.yaml to config.yaml: cp config.example.yaml config.yaml"
        echo -e "  ${RED}→${NC} Then edit config.yaml with your settings"
        return 1
    fi
    
    print_success "config.yaml exists"
    
    # Check if Python is available for YAML validation
    if command -v python3 &> /dev/null; then
        print_info "Validating YAML syntax with Python..."
        
        PYTHON_VALIDATION=$(python3 << 'EOF'
import sys
try:
    import yaml
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    print("VALID")
    sys.exit(0)
except yaml.YAMLError as e:
    print(f"YAML_ERROR: {e}")
    sys.exit(1)
except ImportError:
    print("PYYAML_MISSING")
    sys.exit(2)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
EOF
)
        PYTHON_EXIT_CODE=$?
        
        if [ $PYTHON_EXIT_CODE -eq 0 ]; then
            print_success "config.yaml is valid YAML"
        elif [ $PYTHON_EXIT_CODE -eq 2 ]; then
            print_warning "PyYAML not installed on host, skipping detailed YAML validation"
            echo -e "  ${YELLOW}→${NC} Install PyYAML for validation: pip3 install pyyaml"
        else
            print_error "config.yaml has invalid YAML syntax"
            echo -e "  ${RED}→${NC} Error: $PYTHON_VALIDATION"
            return 1
        fi
    else
        print_warning "Python3 not found, skipping YAML syntax validation"
    fi
    
    return 0
}

check_config_fields() {
    if ! command -v python3 &> /dev/null; then
        print_warning "Python3 not available, skipping config field validation"
        return 0
    fi
    
    FIELD_VALIDATION=$(python3 << 'EOF'
import sys
try:
    import yaml
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    required_fields = ['git_token', 'run_mode', 'cron_schedule']
    optional_fields = ['git_user_name', 'git_user_email']
    
    errors = []
    warnings = []
    
    # Check required fields
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    # Validate git_token
    if 'git_token' in config:
        token = str(config['git_token'])
        if token in ['your_github_token_here', '', 'None']:
            errors.append("git_token is still set to placeholder value")
        elif len(token) < 20:
            warnings.append("git_token seems too short, please verify")
    
    # Validate run_mode
    if 'run_mode' in config:
        if config['run_mode'] not in ['scheduled', 'immediate']:
            errors.append(f"run_mode must be 'scheduled' or 'immediate', got: {config['run_mode']}")
    
    # Validate cron_schedule
    if 'cron_schedule' in config:
        cron = str(config['cron_schedule'])
        parts = cron.split()
        if len(parts) not in [5, 6]:
            errors.append(f"cron_schedule should have 5 or 6 fields, got {len(parts)}: {cron}")
    
    # Check optional fields
    for field in optional_fields:
        if field not in config or not config[field]:
            warnings.append(f"Optional field '{field}' is not set")
    
    if errors:
        print("ERRORS:")
        for error in errors:
            print(f"  - {error}")
    
    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not errors and not warnings:
        print("ALL_VALID")
    
    sys.exit(0 if not errors else 1)

except ImportError:
    print("PYYAML_MISSING")
    sys.exit(2)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
EOF
)
    VALIDATION_EXIT_CODE=$?
    
    if [ $VALIDATION_EXIT_CODE -eq 2 ]; then
        return 0  # PyYAML missing, already warned
    elif [ $VALIDATION_EXIT_CODE -eq 0 ]; then
        if echo "$FIELD_VALIDATION" | grep -q "ALL_VALID"; then
            print_success "All required configuration fields are valid"
        elif echo "$FIELD_VALIDATION" | grep -q "WARNINGS:"; then
            print_success "Required configuration fields are present"
            echo "$FIELD_VALIDATION" | grep -A 100 "WARNINGS:" | grep "^  -" | while read -r line; do
                print_warning "$(echo "$line" | sed 's/^  - //')"
            done
        fi
    else
        echo "$FIELD_VALIDATION" | grep -A 100 "ERRORS:" | grep "^  -" | while read -r line; do
            print_error "$(echo "$line" | sed 's/^  - //')"
        done
        echo "$FIELD_VALIDATION" | grep -A 100 "WARNINGS:" | grep "^  -" | while read -r line; do
            print_warning "$(echo "$line" | sed 's/^  - //')"
        done
        return 1
    fi
    
    return 0
}

check_file_permissions() {
    print_header "4. Checking File Permissions"
    
    # Check entrypoint.sh
    if [ -f "entrypoint.sh" ]; then
        if [ -x "entrypoint.sh" ]; then
            print_success "entrypoint.sh is executable"
        else
            print_warning "entrypoint.sh is not executable (will be fixed by Docker)"
            print_info "You can make it executable with: chmod +x entrypoint.sh"
        fi
    fi
    
    # Check run_and_sync.py
    if [ -f "run_and_sync.py" ]; then
        if [ -r "run_and_sync.py" ]; then
            print_success "run_and_sync.py is readable"
        else
            print_error "run_and_sync.py is not readable"
            echo -e "  ${RED}→${NC} Fix with: chmod +r run_and_sync.py"
            return 1
        fi
    fi
    
    return 0
}

check_directory_structure() {
    print_header "5. Checking Directory Structure"
    
    # Check if logs directory exists or can be created
    if [ -d "logs" ]; then
        print_success "logs/ directory exists"
    else
        print_info "logs/ directory will be created by Docker"
    fi
    
    # Check write permissions for current directory
    if [ -w "." ]; then
        print_success "Current directory is writable"
    else
        print_error "Current directory is not writable"
        echo -e "  ${RED}→${NC} Docker needs write permissions to create logs and sync files"
        return 1
    fi
    
    return 0
}

check_git_repository() {
    print_header "6. Checking Git Repository"
    
    if [ -d ".git" ]; then
        print_success "Current directory is a git repository"
    else
        print_error "Current directory is not a git repository"
        echo -e "  ${RED}→${NC} Initialize with: git init"
        return 1
    fi
    
    # Check remote origin
    if git remote get-url origin &> /dev/null; then
        REMOTE_URL=$(git remote get-url origin)
        print_success "Git remote 'origin' is configured"
        print_info "Remote URL: $REMOTE_URL"
        
        # Verify it's the correct repository
        if echo "$REMOTE_URL" | grep -q "trends-story"; then
            print_success "Remote points to trends-story repository"
        else
            print_warning "Remote may not point to the correct repository"
            echo -e "  ${YELLOW}→${NC} Expected repository containing 'trends-story'"
        fi
    else
        print_error "Git remote 'origin' is not configured"
        echo -e "  ${RED}→${NC} Add remote: git remote add origin <your-repo-url>"
        return 1
    fi
    
    # Check for uncommitted changes
    if git diff-index --quiet HEAD -- 2>/dev/null; then
        print_success "No uncommitted changes detected"
    else
        print_warning "Uncommitted changes detected"
        echo -e "  ${YELLOW}→${NC} Consider committing changes to avoid conflicts during sync"
    fi
    
    return 0
}

check_github_token() {
    if [ "$QUICK" = true ]; then
        print_info "Skipping GitHub token validation (--quick mode)"
        return 0
    fi
    
    print_header "7. Validating GitHub Token (Optional)"
    
    if ! command -v python3 &> /dev/null; then
        print_warning "Python3 not available, skipping token validation"
        return 0
    fi
    
    TOKEN_VALIDATION=$(python3 << 'EOF'
import sys
try:
    import yaml
    import urllib.request
    import json
    
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    token = config.get('git_token', '')
    
    if not token or token in ['your_github_token_here', '', 'None']:
        print("TOKEN_NOT_SET")
        sys.exit(0)
    
    # Test GitHub API with token
    req = urllib.request.Request('https://api.github.com/user')
    req.add_header('Authorization', f'token {token}')
    req.add_header('User-Agent', 'trends-story-validator')
    
    try:
        response = urllib.request.urlopen(req, timeout=10)
        data = json.loads(response.read().decode())
        print(f"VALID:{data.get('login', 'unknown')}")
        
        # Check scopes
        scopes = response.headers.get('X-OAuth-Scopes', '')
        if 'repo' in scopes or 'public_repo' in scopes:
            print("SCOPE_OK")
        else:
            print(f"SCOPE_LIMITED:{scopes}")
        
        sys.exit(0)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("TOKEN_INVALID")
        else:
            print(f"HTTP_ERROR:{e.code}")
        sys.exit(1)
    except Exception as e:
        print(f"NETWORK_ERROR:{e}")
        sys.exit(1)

except ImportError:
    print("PYYAML_MISSING")
    sys.exit(2)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
EOF
)
    VALIDATION_EXIT_CODE=$?
    
    if [ $VALIDATION_EXIT_CODE -eq 2 ]; then
        print_warning "PyYAML not installed, skipping token validation"
        return 0
    fi
    
    if echo "$TOKEN_VALIDATION" | grep -q "TOKEN_NOT_SET"; then
        print_warning "GitHub token not configured in config.yaml"
        echo -e "  ${YELLOW}→${NC} Set git_token in config.yaml before deployment"
        return 0
    elif echo "$TOKEN_VALIDATION" | grep -q "VALID:"; then
        USERNAME=$(echo "$TOKEN_VALIDATION" | grep "VALID:" | cut -d':' -f2)
        print_success "GitHub token is valid (authenticated as: $USERNAME)"
        
        if echo "$TOKEN_VALIDATION" | grep -q "SCOPE_OK"; then
            print_success "GitHub token has repository access permissions"
        elif echo "$TOKEN_VALIDATION" | grep -q "SCOPE_LIMITED:"; then
            SCOPES=$(echo "$TOKEN_VALIDATION" | grep "SCOPE_LIMITED:" | cut -d':' -f2)
            print_warning "GitHub token may have limited permissions"
            print_info "Current scopes: $SCOPES"
            echo -e "  ${YELLOW}→${NC} Ensure token has 'repo' scope for private repos"
        fi
    elif echo "$TOKEN_VALIDATION" | grep -q "TOKEN_INVALID"; then
        print_error "GitHub token is invalid or expired"
        echo -e "  ${RED}→${NC} Generate a new token at: https://github.com/settings/tokens"
        return 1
    elif echo "$TOKEN_VALIDATION" | grep -q "NETWORK_ERROR"; then
        print_warning "Could not validate token (network error)"
        print_info "Token will be validated when container runs"
    else
        print_warning "Could not validate GitHub token"
        print_info "$TOKEN_VALIDATION"
    fi
    
    return 0
}

check_python_environment() {
    print_header "8. Checking Python Environment (Host)"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python 3 is available: $PYTHON_VERSION"
    else
        print_warning "Python 3 not found on host"
        echo -e "  ${YELLOW}→${NC} Python is required in Docker container (already handled)"
        echo -e "  ${YELLOW}→${NC} Install on host for validation: apt-get install python3 (Linux) or brew install python3 (Mac)"
    fi
    
    if command -v python3 &> /dev/null; then
        if python3 -c "import yaml" 2>/dev/null; then
            print_success "PyYAML is installed on host"
        else
            print_warning "PyYAML not installed on host (optional for validation)"
            echo -e "  ${YELLOW}→${NC} Install with: pip3 install pyyaml"
        fi
    fi
    
    return 0
}

print_summary() {
    print_header "Validation Summary"
    
    echo -e "${BLUE}Total Checks:${NC} $TOTAL_CHECKS"
    echo -e "${GREEN}Passed:${NC} $PASSED_CHECKS"
    echo -e "${RED}Failed:${NC} $FAILED_CHECKS"
    echo -e "${YELLOW}Warnings:${NC} $WARNING_CHECKS"
    echo ""
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "${GREEN}✓ All critical checks passed!${NC}"
        echo ""
        echo -e "${BLUE}Next Steps:${NC}"
        echo "  1. Review any warnings above"
        echo "  2. Start the container with: docker-compose up -d"
        echo "  3. View logs with: docker-compose logs -f"
        echo "  4. Stop the container with: docker-compose down"
        echo ""
        echo -e "Validation log saved to: ${BLUE}$LOG_FILE${NC}"
        return 0
    else
        echo -e "${RED}✗ Validation failed with $FAILED_CHECKS error(s)${NC}"
        echo ""
        echo -e "${RED}Please fix the errors above before proceeding.${NC}"
        echo ""
        echo -e "Validation log saved to: ${BLUE}$LOG_FILE${NC}"
        return 1
    fi
}

#############################################################################
# Main Execution
#############################################################################

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -q|--quick)
                QUICK=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Print banner
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         Docker Setup Validation - Trends Story            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo "Starting validation at $(date)" > "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    
    # Run all checks
    check_docker_installed
    check_docker_running
    check_docker_permissions
    check_docker_compose
    check_required_files
    check_config_yaml
    check_config_fields
    check_file_permissions
    check_directory_structure
    check_git_repository
    check_github_token
    check_python_environment
    
    # Print summary and exit
    echo ""
    print_summary
    exit $?
}

# Run main function
main "$@"
#!/bin/bash

# AutoClip system status check script
# Version: 2.0
# Function: Check the running status of AutoClip system services

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

# Service port configuration
BACKEND_PORT=8000
REDIS_PORT=6379

# PID files
BACKEND_PID_FILE="backend.pid"
CELERY_PID_FILE="celery.pid"

# Log directory
LOG_DIR="logs"

# =============================================================================
# Color and style definitions
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Icon definitions
ICON_SUCCESS="✅"
ICON_ERROR="❌"
ICON_WARNING="⚠️"
ICON_INFO="ℹ️"
ICON_HEALTH="💚"
ICON_SICK="🤒"
ICON_ROCKET="🚀"
ICON_DATABASE="🗄️"
ICON_WORKER="👷"
ICON_WEB="🌐"
ICON_REDIS="🔴"

# =============================================================================
# Utility functions
# =============================================================================

log_info() {
    echo -e "${BLUE}${ICON_INFO} $1${NC}"
}

log_success() {
    echo -e "${GREEN}${ICON_SUCCESS} $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}${ICON_WARNING} $1${NC}"
}

log_error() {
    echo -e "${RED}${ICON_ERROR} $1${NC}"
}

log_header() {
    echo -e "\n${PURPLE}${ICON_ROCKET} $1${NC}"
    echo -e "${PURPLE}$(printf '=%.0s' {1..50})${NC}"
}

# Check service health status
check_service_health() {
    local url="$1"
    local service_name="$2"
    
    if curl -fsS "$url" >/dev/null 2>&1; then
        echo -e "${GREEN}${ICON_HEALTH} $service_name healthy${NC}"
        return 0
    else
        echo -e "${RED}${ICON_SICK} $service_name unhealthy${NC}"
        return 1
    fi
}

# Check process status
check_process_status() {
    local pid_file="$1"
    local service_name="$2"
    local process_pattern="$3"
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}${ICON_SUCCESS} $service_name running (PID: $pid)${NC}"
            return 0
        else
            echo -e "${RED}${ICON_ERROR} $service_name PID file exists but process not found${NC}"
            return 1
        fi
    else
        # Check if related processes are running
        if pgrep -f "$process_pattern" >/dev/null; then
            local pids=$(pgrep -f "$process_pattern" | tr '\n' ' ')
            echo -e "${YELLOW}${ICON_WARNING} $service_name running but no PID file (PIDs: $pids)${NC}"
            return 0
        else
            echo -e "${RED}${ICON_ERROR} $service_name not running${NC}"
            return 1
        fi
    fi
}

# Get service information
get_service_info() {
    local service_name="$1"
    local pid_file="$2"
    local process_pattern="$3"
    
    echo -e "\n${CYAN}📊 $service_name Details:${NC}"
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  PID: $pid"
            echo "  Process Info:"
            ps -p "$pid" -o pid,ppid,etime,pcpu,pmem,cmd --no-headers 2>/dev/null | while read line; do
                echo "    $line"
            done
        fi
    else
        local pids=$(pgrep -f "$process_pattern" 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            echo "  PIDs: $pids"
            echo "  Process Info:"
            echo "$pids" | while read pid; do
                ps -p "$pid" -o pid,ppid,etime,pcpu,pmem,cmd --no-headers 2>/dev/null | while read line; do
                    echo "    $line"
                done
            done
        fi
    fi
}

# =============================================================================
# Check functions
# =============================================================================

check_redis() {
    log_header "Redis Service Status"
    
    if redis-cli ping >/dev/null 2>&1; then
        log_success "Redis service is running normally"
        
        # Get Redis information
        echo -e "\n${CYAN}📊 Redis Details:${NC}"
        redis-cli info server | grep -E "(redis_version|uptime_in_seconds|connected_clients)" | while read line; do
            echo "  $line"
        done
        return 0
    else
        log_error "Redis service is not running or cannot connect"
        return 1
    fi
}

check_backend() {
    log_header "Backend API Service Status"
    
    # Check process status
    if check_process_status "$BACKEND_PID_FILE" "Backend Service" "uvicorn.*backend.main:app"; then
        # Check health status
        if check_service_health "http://localhost:$BACKEND_PORT/api/v1/health/" "Backend API"; then
            get_service_info "Backend Service" "$BACKEND_PID_FILE" "uvicorn.*backend.main:app"
            return 0
        else
            log_warning "Backend process running but API not responding"
            return 1
        fi
    else
        return 1
    fi
}



check_celery() {
    log_header "Celery Worker Status"
    
    # Check process status
    if check_process_status "$CELERY_PID_FILE" "Celery Worker" "celery.*worker"; then
        get_service_info "Celery Worker" "$CELERY_PID_FILE" "celery.*worker"
        
        # Check Celery connection
        if command -v celery >/dev/null 2>&1; then
            echo -e "\n${CYAN}📊 Celery Details:${NC}"
            if PYTHONPATH="${PWD}:${PYTHONPATH:-}" celery -A backend.core.celery_app inspect active >/dev/null 2>&1; then
                log_success "Celery connection is normal"
                
                # Get active tasks
                local active_tasks=$(PYTHONPATH="${PWD}:${PYTHONPATH:-}" celery -A backend.core.celery_app inspect active 2>/dev/null | jq -r '.[] | length' 2>/dev/null || echo "0")
                echo "  Active tasks: $active_tasks"
            else
                log_warning "Celery connection test failed"
            fi
        fi
        return 0
    else
        return 1
    fi
}

check_database() {
    log_header "Database Status"
    
    if [[ -f "data/autoclip.db" ]]; then
        log_success "Database file exists"
        
        # Get database information
        echo -e "\n${CYAN}📊 Database Details:${NC}"
        local db_size=$(du -h "data/autoclip.db" 2>/dev/null | cut -f1)
        echo "  File size: $db_size"
        
        # Check database connection
        if python -c "
import sys
sys.path.insert(0, '.')
from backend.core.database import test_connection
if test_connection():
    print('Database connection is normal')
else:
    print('Database connection failed')
    sys.exit(1)
" 2>/dev/null; then
            log_success "Database connection is normal"
        else
            log_error "Database connection failed"
            return 1
        fi
    else
        log_warning "Database file not found"
        return 1
    fi
}

check_logs() {
    log_header "Log File Status"
    
    if [[ -d "$LOG_DIR" ]]; then
        log_success "Log directory exists"
        
        echo -e "\n${CYAN}📊 Log File Information:${NC}"
        ls -la "$LOG_DIR"/*.log 2>/dev/null | while read line; do
            echo "  $line"
        done
        
        # Display latest logs
        echo -e "\n${CYAN}📝 Latest Logs (Last 10 lines):${NC}"
        for log_file in "$LOG_DIR"/*.log; do
            if [[ -f "$log_file" ]]; then
                echo -e "\n${YELLOW}$(basename "$log_file"):${NC}"
                tail -n 5 "$log_file" 2>/dev/null | while read line; do
                    echo "  $line"
                done
            fi
        done
    else
        log_warning "Log directory not found"
    fi
}

# =============================================================================
# Main function
# =============================================================================

main() {
    log_header "AutoClip System Status Check v2.0"
    
    local overall_status=0
    
    # Check each service
    check_redis || overall_status=1
    check_database || overall_status=1
    check_celery || overall_status=1
    check_backend || overall_status=1
    check_logs
    
    # Display overall status
    log_header "Overall System Status"
    
    if [[ $overall_status -eq 0 ]]; then
        log_success "All services are running normally"
        echo ""
        echo -e "${WHITE}🎉 AutoClip system is fully healthy!${NC}"
        echo ""
        echo -e "${CYAN}🌐 Access URLs:${NC}"
        echo -e "  Backend API:  http://localhost:$BACKEND_PORT"
        echo -e "  API Docs:     http://localhost:$BACKEND_PORT/docs"
    else
        log_error "Some services have issues"
        echo ""
        echo -e "${YELLOW}💡 Recommended Actions:${NC}"
        echo -e "  1. Check log files for detailed error information"
        echo -e "  2. Restart system: ./stop_autoclip.sh && ./start_autoclip.sh"
        echo -e "  3. Check environment configuration and dependencies"
    fi
    
    echo ""
    echo -e "${CYAN}📋 Common Commands:${NC}"
    echo -e "  Start system: ./start_autoclip.sh"
    echo -e "  Stop system:  ./stop_autoclip.sh"
    echo -e "  View logs:    tail -f $LOG_DIR/*.log"
}

# Run main function
main "$@"

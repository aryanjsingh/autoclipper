#!/bin/bash

# AutoClip system stop script
# Version: 2.0
# Function: Gracefully stop all AutoClip services

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

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
NC='\033[0m' # No Color

# Icon definitions
ICON_SUCCESS="✅"
ICON_ERROR="❌"
ICON_WARNING="⚠️"
ICON_INFO="ℹ️"
ICON_STOP="🛑"
ICON_CLEAN="🧹"

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
    echo -e "\n${PURPLE}${ICON_STOP} $1${NC}"
    echo -e "${PURPLE}$(printf '=%.0s' {1..50})${NC}"
}

# Stop a process
stop_process() {
    local pid_file="$1"
    local service_name="$2"
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping $service_name (PID: $pid)..."
            
            # Graceful stop
            kill "$pid" 2>/dev/null || true
            
            # Wait for process to end
            local count=0
            while kill -0 "$pid" 2>/dev/null && [[ $count -lt 10 ]]; do
                sleep 1
                ((count++))
            done
            
            # Force stop if process is still running
            if kill -0 "$pid" 2>/dev/null; then
                log_warning "Force stopping $service_name..."
                kill -9 "$pid" 2>/dev/null || true
                sleep 1
            fi
            
            if kill -0 "$pid" 2>/dev/null; then
                log_error "Unable to stop $service_name"
            else
                log_success "$service_name stopped"
            fi
        else
            log_warning "$service_name process not found"
        fi
        rm -f "$pid_file"
    else
        log_info "$service_name PID file not found"
    fi
}

# Stop all related processes
stop_all_processes() {
    log_header "Stopping All AutoClip Services"
    
    # Stop processes managed by PID files
    stop_process "$BACKEND_PID_FILE" "Backend Service"
    stop_process "$CELERY_PID_FILE" "Celery Worker"

    # Stop all related processes
    log_info "Stopping all Celery Worker processes..."
    pkill -f "celery.*worker" 2>/dev/null || true

    log_info "Stopping all backend API processes..."
    pkill -f "uvicorn.*backend.main:app" 2>/dev/null || true
    
    # Wait for processes to completely stop
    sleep 2
    
    log_success "All services stopped"
}

# Clean up temporary files
cleanup_temp_files() {
    log_header "Cleaning Up Temporary Files"
    
    # Clean up PID files
    rm -f "$BACKEND_PID_FILE" "$CELERY_PID_FILE"
    log_success "PID files cleaned up"
    
    # Clean up Celery temporary files
    rm -f /tmp/celerybeat-schedule /tmp/celerybeat.pid 2>/dev/null || true
    log_success "Celery temporary files cleaned up"
    
    # Clean up Python cache
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    log_success "Python cache cleaned up"
}

# Display system status
show_system_status() {
    log_header "System Status Check"
    
    local services_running=false
    
    # Check backend service
    if pgrep -f "uvicorn.*backend.main:app" >/dev/null; then
        log_warning "Backend service is still running"
        services_running=true
    else
        log_success "Backend service stopped"
    fi
    
    # Check Celery Worker
    if pgrep -f "celery.*worker" >/dev/null; then
        log_warning "Celery Worker is still running"
        services_running=true
    else
        log_success "Celery Worker stopped"
    fi
    
    if [[ "$services_running" == true ]]; then
        log_warning "Some services are still running, manual stop may be required"
        echo ""
        echo "Processes still running:"
        pgrep -f "uvicorn.*backend.main:app\|celery.*worker" | while read pid; do
            ps -p "$pid" -o pid,ppid,cmd --no-headers 2>/dev/null || true
        done
    else
        log_success "All AutoClip services have been completely stopped"
    fi
}

# Display log information
show_log_info() {
    log_header "Log File Information"
    
    if [[ -d "$LOG_DIR" ]]; then
        echo "Log file location:"
        ls -la "$LOG_DIR"/*.log 2>/dev/null | while read line; do
            echo "  $line"
        done
        echo ""
        echo "View latest logs:"
        echo "  Backend log: tail -f $LOG_DIR/backend.log"
        echo "  Celery log: tail -f $LOG_DIR/celery.log"
    else
        log_info "Log directory not found"
    fi
}

# =============================================================================
# Main function
# =============================================================================

main() {
    log_header "AutoClip System Stopper v2.0"
    
    # Stop all services
    stop_all_processes
    
    # Clean up temporary files
    cleanup_temp_files
    
    # Display system status
    show_system_status
    
    # Display log information
    show_log_info
    
    echo ""
    log_success "AutoClip system has been completely stopped"
    echo ""
    echo "To restart, run: ./start_autoclip.sh"
}

# Run main function
main "$@"

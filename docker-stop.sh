#!/bin/bash

# AutoClip Docker stop script
# Version: 1.0
# Function: Stop AutoClip Docker services

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

# Color definitions
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

# =============================================================================
# Stop functions
# =============================================================================

stop_services() {
    log_header "Stopping AutoClip Services"
    
    local mode="${1:-production}"
    local compose_file="docker-compose.yml"
    
    if [[ "$mode" == "dev" ]]; then
        compose_file="docker-compose.dev.yml"
    fi
    
    log_info "Stopping services (mode: $mode)..."
    
    # Stop services
    if docker-compose -f "$compose_file" down; then
        log_success "Services stopped"
    else
        log_error "Failed to stop services"
        exit 1
    fi
}

cleanup_containers() {
    log_header "Cleaning Up Containers"
    
    # Stop all related containers
    local containers=$(docker ps -a --filter "name=autoclip" --format "{{.Names}}" 2>/dev/null || true)
    
    if [[ -n "$containers" ]]; then
        log_info "Found the following AutoClip containers:"
        echo "$containers"
        
        if [[ "${1:-}" == "--force" ]]; then
            log_info "Force stopping all containers..."
            echo "$containers" | xargs docker stop 2>/dev/null || true
            echo "$containers" | xargs docker rm 2>/dev/null || true
            log_success "Container cleanup completed"
        else
            log_warning "Use --force parameter to force cleanup containers"
        fi
    else
        log_success "No AutoClip containers found"
    fi
}

cleanup_images() {
    log_header "Cleaning Up Images"
    
    if [[ "${1:-}" == "--force" ]]; then
        log_info "Cleaning up unused images..."
        docker image prune -f
        log_success "Image cleanup completed"
    else
        log_info "Use --force parameter to clean up unused images"
    fi
}

cleanup_volumes() {
    log_header "Cleaning Up Volumes"
    
    if [[ "${1:-}" == "--force" ]]; then
        log_warning "This will delete all data, including project files and databases!"
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Cleaning up volumes..."
            docker volume prune -f
            log_success "Volume cleanup completed"
        else
            log_info "Volume cleanup cancelled"
        fi
    else
        log_info "Use --force parameter to clean up unused volumes"
    fi
}

show_status() {
    log_header "Current Status"
    
    echo -e "${BLUE}Container Status:${NC}"
    docker-compose ps 2>/dev/null || echo "  No running services"
    
    echo -e "\n${BLUE}AutoClip Related Containers:${NC}"
    docker ps -a --filter "name=autoclip" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  No related containers found"
    
    echo -e "\n${BLUE}Volumes:${NC}"
    docker volume ls --filter "name=autoclip" --format "table {{.Name}}\t{{.Driver}}\t{{.Size}}" 2>/dev/null || echo "  No related volumes found"
}

# =============================================================================
# Main function
# =============================================================================

main() {
    local mode="production"
    local cleanup=false
    local force=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            "dev")
                mode="development"
                shift
                ;;
            "--cleanup")
                cleanup=true
                shift
                ;;
            "--force")
                force=true
                shift
                ;;
            "help"|"-h"|"--help")
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown parameter: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    log_header "AutoClip Docker Stopper v1.0"
    
    # Stop services
    stop_services "$mode"
    
    # Cleanup (if needed)
    if [[ "$cleanup" == true ]]; then
        cleanup_containers "$force"
        cleanup_images "$force"
        cleanup_volumes "$force"
    fi
    
    # Show status
    show_status
    
    echo -e "\n${GREEN}AutoClip Docker services stopped${NC}"
}

# Show help information
show_help() {
    echo "AutoClip Docker stop script"
    echo ""
    echo "Usage:"
    echo "  $0 [options]"
    echo ""
    echo "Options:"
    echo "  dev          Stop development environment"
    echo "  --cleanup    Clean up resources after stopping"
    echo "  --force      Force cleanup (including data)"
    echo "  help         Show help information"
    echo ""
    echo "Examples:"
    echo "  $0                    # Stop production environment"
    echo "  $0 dev                # Stop development environment"
    echo "  $0 --cleanup          # Stop and clean up resources"
    echo "  $0 --cleanup --force  # Stop and force cleanup all resources"
    echo "  $0 help               # Show help"
    echo ""
    echo "Note:"
    echo "  --force parameter will delete all data, use with caution!"
}

# Run main function
main "$@"

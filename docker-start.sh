#!/bin/bash

# AutoClip Docker startup script
# Version: 1.0
# Function: Quickly start AutoClip system using Docker

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
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Icon definitions
ICON_SUCCESS="✅"
ICON_ERROR="❌"
ICON_WARNING="⚠️"
ICON_INFO="ℹ️"
ICON_ROCKET="🚀"
ICON_DOCKER="🐳"

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

# =============================================================================
# Check functions
# =============================================================================

check_docker() {
    log_header "Checking Docker Environment"
    
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed, please install Docker first"
        exit 1
    fi
    log_success "Docker is installed"
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "Docker Compose is not installed, please install Docker Compose first"
        exit 1
    fi
    log_success "Docker Compose is installed"
    
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker service is not running, please start Docker service"
        exit 1
    fi
    log_success "Docker service is running normally"
}

check_environment() {
    log_header "Checking Environment Configuration"
    
    if [[ ! -f ".env" ]]; then
        log_warning ".env file not found, creating default configuration..."
        if [[ -f "env.example" ]]; then
            cp env.example .env
            log_success "Default .env file created"
            log_warning "Please edit .env file and fill in necessary configuration (especially API key)"
        else
            log_error "env.example file not found"
            exit 1
        fi
    else
        log_success ".env file exists"
    fi
    
    # Check required configuration
    if ! grep -q "API_DASHSCOPE_API_KEY" .env || grep -q "API_DASHSCOPE_API_KEY=$" .env; then
        log_warning "API_DASHSCOPE_API_KEY is not configured, AI features will be unavailable"
    fi
}

check_ports() {
    log_header "Checking Port Usage"
    
    local ports=(8000 3000 6379 5555)
    local occupied_ports=()
    
    for port in "${ports[@]}"; do
        if lsof -i ":$port" >/dev/null 2>&1; then
            occupied_ports+=("$port")
        fi
    done
    
    if [[ ${#occupied_ports[@]} -gt 0 ]]; then
        log_warning "The following ports are in use: ${occupied_ports[*]}"
        log_info "Docker will handle port conflicts automatically, but it is recommended to stop services using these ports first"
    else
        log_success "All ports are available"
    fi
}

# =============================================================================
# Startup functions
# =============================================================================

start_services() {
    log_header "Starting AutoClip Services"
    
    # Select startup mode
    if [[ "${1:-}" == "dev" ]]; then
        log_info "Starting development environment..."
        docker-compose -f docker-compose.dev.yml up -d
        COMPOSE_FILE="docker-compose.dev.yml"
    else
        log_info "Starting production environment..."
        docker-compose up -d
        COMPOSE_FILE="docker-compose.yml"
    fi
    
    # Wait for services to start
    log_info "Waiting for services to start..."
    sleep 10
    
    # Check service status
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        log_success "Services started successfully"
    else
        log_error "Failed to start services"
        log_info "View logs: docker-compose -f $COMPOSE_FILE logs"
        exit 1
    fi
}

show_status() {
    log_header "Service Status"
    
    echo -e "${CYAN}Container Status:${NC}"
    docker-compose ps
    
    echo -e "\n${CYAN}Access URLs:${NC}"
    echo -e "  Frontend: http://localhost:3000"
    echo -e "  Backend API:  http://localhost:8000"
    echo -e "  API Docs: http://localhost:8000/docs"
    echo -e "  Flower Monitor: http://localhost:5555"
    
    echo -e "\n${CYAN}Common Commands:${NC}"
    echo -e "  View logs: docker-compose logs -f"
    echo -e "  Stop services: docker-compose down"
    echo -e "  Restart services: docker-compose restart"
    echo -e "  Enter container: docker-compose exec autoclip bash"
}

# =============================================================================
# Main function
# =============================================================================

main() {
    log_header "AutoClip Docker Launcher v1.0"
    
    # Parse arguments
    local mode="production"
    if [[ "${1:-}" == "dev" ]]; then
        mode="development"
    fi
    
    log_info "Startup mode: $mode"
    
    # Run checks
    check_docker
    check_environment
    check_ports
    
    # Start services
    start_services "$mode"
    
    # Show status
    show_status
    
    echo -e "\n${WHITE}AutoClip Docker deployment completed!${NC}"
    echo -e "${YELLOW}Tip: First startup may take a few minutes to download and build images${NC}"
}

# Show help information
show_help() {
    echo "AutoClip Docker startup script"
    echo ""
    echo "Usage:"
    echo "  $0 [options]"
    echo ""
    echo "Options:"
    echo "  dev     Start development environment"
    echo "  help    Show help information"
    echo ""
    echo "Examples:"
    echo "  $0          # Start production environment"
    echo "  $0 dev      # Start development environment"
    echo "  $0 help     # Show help"
}

# Handle arguments
case "${1:-}" in
    "help"|"-h"|"--help")
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac

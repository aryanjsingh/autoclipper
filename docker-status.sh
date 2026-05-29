#!/bin/bash

# AutoClip Docker status check script
# Version: 1.0
# Function: Check AutoClip Docker service status

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
ICON_HEALTH="💚"
ICON_SICK="🤒"
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
    log_header "Docker Environment Check"
    
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed"
        return 1
    fi
    log_success "Docker is installed"
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "Docker Compose is not installed"
        return 1
    fi
    log_success "Docker Compose is installed"
    
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker service is not running"
        return 1
    fi
    log_success "Docker service is running normally"
    
    return 0
}

check_containers() {
    log_header "Container Status Check"
    
    local containers=$(docker ps -a --filter "name=autoclip" --format "{{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true)
    
    if [[ -z "$containers" ]]; then
        log_warning "No AutoClip containers found"
        return 1
    fi
    
    echo -e "${CYAN}Container Status:${NC}"
    echo "$containers" | while IFS=$'\t' read -r name status ports; do
        if [[ "$status" == *"Up"* ]]; then
            echo -e "  ${GREEN}${ICON_HEALTH} $name${NC} - $status"
        else
            echo -e "  ${RED}${ICON_SICK} $name${NC} - $status"
        fi
    done
    
    return 0
}

check_services() {
    log_header "Service Health Check"
    
    # Check backend API
    if curl -fsS "http://localhost:8000/api/v1/health/" >/dev/null 2>&1; then
        log_success "Backend API service is healthy"
    else
        log_error "Backend API service is unhealthy"
    fi
    
    # Check frontend service
    if curl -fsS "http://localhost:3000/" >/dev/null 2>&1; then
        log_success "Frontend service is healthy"
    else
        log_error "Frontend service is unhealthy"
    fi
    
    # Check Redis
    if docker exec autoclip-redis redis-cli ping >/dev/null 2>&1; then
        log_success "Redis service is healthy"
    else
        log_error "Redis service is unhealthy"
    fi
}

check_volumes() {
    log_header "Volume Check"
    
    local volumes=$(docker volume ls --filter "name=autoclip" --format "{{.Name}}\t{{.Driver}}\t{{.Size}}" 2>/dev/null || true)
    
    if [[ -z "$volumes" ]]; then
        log_warning "No AutoClip volumes found"
        return 1
    fi
    
    echo -e "${CYAN}Volumes:${NC}"
    echo "$volumes" | while IFS=$'\t' read -r name driver size; do
        echo -e "  ${ICON_INFO} $name ($driver) - $size"
    done
    
    return 0
}

check_networks() {
    log_header "Network Check"
    
    local networks=$(docker network ls --filter "name=autoclip" --format "{{.Name}}\t{{.Driver}}\t{{.Scope}}" 2>/dev/null || true)
    
    if [[ -z "$networks" ]]; then
        log_warning "No AutoClip networks found"
        return 1
    fi
    
    echo -e "${CYAN}Networks:${NC}"
    echo "$networks" | while IFS=$'\t' read -r name driver scope; do
        echo -e "  ${ICON_INFO} $name ($driver) - $scope"
    done
    
    return 0
}

check_resources() {
    log_header "Resource Usage"
    
    echo -e "${CYAN}Container Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" $(docker ps --filter "name=autoclip" --format "{{.Names}}" 2>/dev/null || true) 2>/dev/null || log_warning "Unable to get resource usage"
}

show_access_info() {
    log_header "Access Information"
    
    echo -e "${CYAN}Service Access URLs:${NC}"
    echo -e "  Frontend: http://localhost:3000"
    echo -e "  Backend API: http://localhost:8000"
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
    log_header "AutoClip Docker Status Check v1.0"
    
    local overall_status=0
    
    # Check Docker environment
    if ! check_docker; then
        overall_status=1
    fi
    
    # Check container status
    if ! check_containers; then
        overall_status=1
    fi
    
    # Check service health status
    check_services
    
    # Check volumes
    check_volumes
    
    # Check networks
    check_networks
    
    # Check resource usage
    check_resources
    
    # Show access information
    show_access_info
    
    # Show overall status
    log_header "Overall Status"
    
    if [[ $overall_status -eq 0 ]]; then
        log_success "AutoClip Docker services are running normally"
        echo -e "\n${WHITE}All services are healthy!${NC}"
    else
        log_error "Some services have issues"
        echo -e "\n${YELLOW}Recommended Actions:${NC}"
        echo -e "  1. View detailed logs: docker-compose logs"
        echo -e "  2. Restart services: docker-compose restart"
        echo -e "  3. Restart: ./docker-start.sh"
    fi
}

# Show help information
show_help() {
    echo "AutoClip Docker status check script"
    echo ""
    echo "Usage:"
    echo "  $0 [options]"
    echo ""
    echo "Options:"
    echo "  help    Show help information"
    echo ""
    echo "Examples:"
    echo "  $0          # Check service status"
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

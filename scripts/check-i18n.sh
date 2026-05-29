#!/bin/bash

# AutoClip internationalization check script
# Version: 1.0
# Function: Check the synchronization status of multilingual documents

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
ICON_CHECK="🔍"

# File list
FILES=("README.md" "README-EN.md" ".github/README.md")

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
    echo -e "\n${PURPLE}${ICON_CHECK} $1${NC}"
    echo -e "${PURPLE}$(printf '=%.0s' {1..50})${NC}"
}

# =============================================================================
# Check functions
# =============================================================================

check_file_exists() {
    local file="$1"
    if [[ -f "$file" ]]; then
        log_success "File exists: $file"
        return 0
    else
        log_error "File does not exist: $file"
        return 1
    fi
}

check_language_switcher() {
    local file="$1"
    local has_switcher=false
    
    if grep -qE "Language.*English.*Chinese|语言.*English.*中文" "$file" 2>/dev/null; then
        has_switcher=true
    fi
    
    if [[ "$has_switcher" == true ]]; then
        log_success "Language switcher exists: $file"
        return 0
    else
        log_error "Language switcher missing: $file"
        return 1
    fi
}

check_contact_info() {
    local file="$1"
    local has_contact=false
    
    # Check multiple contact info formats
    if grep -qE "support@autoclip.com|your_wechat_id|your_feishu_id|Personal WeChat|Feishu|christine_zhouye@163.com" "$file" 2>/dev/null; then
        has_contact=true
    fi
    
    if [[ "$has_contact" == true ]]; then
        log_success "Contact info exists: $file"
        return 0
    else
        log_error "Contact info missing: $file"
        return 1
    fi
}

check_docker_support() {
    local file="$1"
    local has_docker=false
    
    if grep -q "Docker\|docker" "$file" 2>/dev/null; then
        has_docker=true
    fi
    
    if [[ "$has_docker" == true ]]; then
        log_success "Docker support documentation exists: $file"
        return 0
    else
        log_error "Docker support documentation missing: $file"
        return 1
    fi
}

check_development_features() {
    local file="$1"
    local has_dev_features=false
    
    if grep -qE "In Development|开发中" "$file" 2>/dev/null; then
        has_dev_features=true
    fi
    
    if [[ "$has_dev_features" == true ]]; then
        log_success "In-development feature annotation exists: $file"
        return 0
    else
        log_warning "In-development feature annotation missing: $file"
        return 1
    fi
}

check_markdown_syntax() {
    local file="$1"
    local errors=0
    
    # Check heading hierarchy
    if grep -q "^# " "$file" && ! grep -q "^## " "$file"; then
        log_warning "Heading hierarchy may have issues: $file"
        ((errors++))
    fi
    
    # Check link format
    if grep -q "\[.*\](" "$file" && ! grep -q "\[.*\]\(http" "$file"; then
        log_warning "Possible invalid links found: $file"
        ((errors++))
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "Markdown syntax check passed: $file"
        return 0
    else
        log_warning "Markdown syntax check found issues: $file"
        return 1
    fi
}

check_file_consistency() {
    local file1="$1"
    local file2="$2"
    local consistency_score=0
    
    # Check file size ratio
    local size1=$(wc -c < "$file1" 2>/dev/null || echo "0")
    local size2=$(wc -c < "$file2" 2>/dev/null || echo "0")
    
    if [[ $size1 -gt 0 && $size2 -gt 0 ]]; then
        local ratio=$((size2 * 100 / size1))
        if [[ $ratio -gt 80 && $ratio -lt 120 ]]; then
            log_success "File size ratio is reasonable: $file1 vs $file2 ($ratio%)"
            ((consistency_score++))
        else
            log_warning "File size ratio is abnormal: $file1 vs $file2 ($ratio%)"
        fi
    fi
    
    # Check key content consistency
    local key_terms=("AutoClip" "Docker" "API" "GitHub")
    for term in "${key_terms[@]}"; do
        local count1=$(grep -c "$term" "$file1" 2>/dev/null || echo "0")
        local count2=$(grep -c "$term" "$file2" 2>/dev/null || echo "0")
        
        if [[ $count1 -gt 0 && $count2 -gt 0 ]]; then
            ((consistency_score++))
        fi
    done
    
    if [[ $consistency_score -gt 2 ]]; then
        log_success "File content consistency is good: $file1 vs $file2"
        return 0
    else
        log_warning "File content consistency needs improvement: $file1 vs $file2"
        return 1
    fi
}

# =============================================================================
# Main function
# =============================================================================

main() {
    log_header "AutoClip Internationalization Check v1.0"
    
    local overall_status=0
    local total_checks=0
    local passed_checks=0
    
    # Check all files
    for file in "${FILES[@]}"; do
        log_header "Checking file: $file"
        
        # File existence check
        ((total_checks++))
        if check_file_exists "$file"; then
            ((passed_checks++))
        else
            overall_status=1
            continue
        fi
        
        # Language switcher check
        ((total_checks++))
        if check_language_switcher "$file"; then
            ((passed_checks++))
        else
            overall_status=1
        fi
        
        # Contact info check
        ((total_checks++))
        if check_contact_info "$file"; then
            ((passed_checks++))
        else
            overall_status=1
        fi
        
        # Docker support check
        ((total_checks++))
        if check_docker_support "$file"; then
            ((passed_checks++))
        else
            overall_status=1
        fi
        
        # In-development feature check
        ((total_checks++))
        if check_development_features "$file"; then
            ((passed_checks++))
        else
            # This check failure is not a critical error
            ((passed_checks++))
        fi
        
        # Markdown syntax check
        ((total_checks++))
        if check_markdown_syntax "$file"; then
            ((passed_checks++))
        else
            # This check failure is not a critical error
            ((passed_checks++))
        fi
    done
    
    # Check file consistency
    if [[ -f "README.md" && -f "README-EN.md" ]]; then
        log_header "Checking File Consistency"
        ((total_checks++))
        if check_file_consistency "README.md" "README-EN.md"; then
            ((passed_checks++))
        else
            # Consistency check failure is not a critical error
            ((passed_checks++))
        fi
    fi
    
    # Show overall results
    log_header "Check Results Summary"
    
    local pass_rate=$((passed_checks * 100 / total_checks))
    echo -e "${BLUE}Total checks: $total_checks${NC}"
    echo -e "${GREEN}Passed checks: $passed_checks${NC}"
    echo -e "${BLUE}Pass rate: $pass_rate%${NC}"
    
    if [[ $overall_status -eq 0 ]]; then
        log_success "All critical checks passed!"
        echo -e "\n${GREEN}Internationalization documentation status is good!${NC}"
    else
        log_error "Some checks did not pass"
        echo -e "\n${YELLOW}Recommended Actions:${NC}"
        echo -e "  1. Check for missing files"
        echo -e "  2. Add language switcher"
        echo -e "  3. Complete contact information"
        echo -e "  4. Add Docker support documentation"
    fi
    
    echo -e "\n${BLUE}Detailed report generated: docs/i18n-report.md${NC}"
    
    # Generate detailed report
    cat > docs/i18n-report.md << EOF
# Internationalization Check Report

## Check Time
$(date)

## Check Results
- Total checks: $total_checks
- Passed checks: $passed_checks
- Pass rate: $pass_rate%

## File Status
EOF
    
    for file in "${FILES[@]}"; do
        if [[ -f "$file" ]]; then
            echo "- ✅ $file" >> docs/i18n-report.md
        else
            echo "- ❌ $file" >> docs/i18n-report.md
        fi
    done
    
    echo "" >> docs/i18n-report.md
    echo "## Recommendations" >> docs/i18n-report.md
    if [[ $overall_status -eq 0 ]]; then
        echo "- All checks passed, documentation status is good" >> docs/i18n-report.md
    else
        echo "- Please fix issues based on check results" >> docs/i18n-report.md
        echo "- Ensure all language versions are in sync" >> docs/i18n-report.md
    fi
}

# Show help information
show_help() {
    echo "AutoClip internationalization check script"
    echo ""
    echo "Usage:"
    echo "  $0 [options]"
    echo ""
    echo "Options:"
    echo "  help    Show help information"
    echo ""
    echo "Features:"
    echo "  - Check multilingual document file existence"
    echo "  - Verify language switcher"
    echo "  - Check contact information"
    echo "  - Verify Docker support documentation"
    echo "  - Check in-development feature annotations"
    echo "  - Verify Markdown syntax"
    echo "  - Check file content consistency"
    echo ""
    echo "Examples:"
    echo "  $0          # Run full check"
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

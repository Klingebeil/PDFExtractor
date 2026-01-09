#!/bin/bash
set -euo pipefail

# Script metadata
readonly SCRIPT_VERSION="1.1.0"
readonly SCRIPT_NAME="PDFExtractor"

# Dynamic path detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR"
VENV_PATH="$SCRIPT_DIR/venv"
SCRIPT_PATH="$SCRIPT_DIR/extract_annotations.py"

# Initialize variables
PAGE_NUMBER=""
LOG_LEVEL="INFO"
INPUT_FILE=""
LOG_FILE=""

# Logging infrastructure
setup_logging() {
    LOG_FILE="$OUTPUT_DIR/pdfextractor.log"
    
    # Initialize log file (overwrite existing)
    cat > "$LOG_FILE" << EOF
PDFExtractor Log - Started at $(date)
=====================================
Script: $0
Arguments: $*
Working Directory: $(pwd)
User: $(whoami)
Version: $SCRIPT_VERSION

EOF
}

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Log to file
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    # Log to console based on level
    case "$level" in
        ERROR)
            echo "[ERROR] $message" >&2
            ;;
        WARNING)
            echo "[WARNING] $message" >&2
            ;;
        INFO)
            if [[ "$LOG_LEVEL" == "DEBUG" || "$LOG_LEVEL" == "INFO" ]]; then
                echo "[INFO] $message"
            fi
            ;;
        DEBUG)
            if [[ "$LOG_LEVEL" == "DEBUG" ]]; then
                echo "[DEBUG] $message"
            fi
            ;;
    esac
}

# Global error handler and cleanup
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log "ERROR" "Script failed with exit code $exit_code"
        echo "[ERROR] Check the log file for details: $LOG_FILE" >&2
    fi
    
    # Deactivate virtual environment if active
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        deactivate 2>/dev/null || true
    fi
    
    exit $exit_code
}

trap cleanup EXIT ERR

# Environment validation
check_environment() {
    log "DEBUG" "Checking environment requirements..."
    
    # Check for OpenAI API key
    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
        log "ERROR" "OPENAI_API_KEY environment variable not set"
        echo "[INFO] Please set your OpenAI API key:" >&2
        echo "  export OPENAI_API_KEY='your-key-here'" >&2
        return 1
    fi
    
    # Basic API key format validation
    if [[ ! "${OPENAI_API_KEY}" =~ ^sk-[a-zA-Z0-9]{20,}$ ]]; then
        log "WARNING" "API key format seems invalid. Expected format: sk-..."
    fi
    
    log "INFO" "OpenAI API key found and validated"
    return 0
}

# Input validation functions
validate_input_file() {
    local file_path="$1"
    
    if [[ -z "$file_path" ]]; then
        log "ERROR" "No input file provided"
        return 1
    fi
    
    if [[ ! -f "$file_path" ]]; then
        log "ERROR" "File does not exist: $file_path"
        return 1
    fi
    
    # Check file extension
    if [[ ! "$file_path" =~ \.(pdf|PDF)$ ]]; then
        log "WARNING" "File may not be a PDF: $file_path"
    fi
    
    log "INFO" "Input file validated: $file_path"
    return 0
}

validate_page_number() {
    local page_num="$1"
    
    if [[ -n "$page_num" ]]; then
        if ! [[ "$page_num" =~ ^[1-9][0-9]*$ ]]; then
            log "ERROR" "Invalid page number: $page_num. Must be a positive integer."
            return 1
        fi
        log "DEBUG" "Page number validated: $page_num"
    fi
    return 0
}

# Virtual environment setup with error handling
setup_virtual_environment() {
    log "DEBUG" "Setting up virtual environment at: $VENV_PATH"
    
    if [[ ! -d "$VENV_PATH" ]]; then
        log "ERROR" "Virtual environment not found at: $VENV_PATH"
        echo "[INFO] Please create it with: python3 -m venv $VENV_PATH" >&2
        return 1
    fi
    
    if [[ ! -f "$VENV_PATH/bin/activate" ]]; then
        log "ERROR" "Virtual environment activation script not found"
        return 1
    fi
    
    # shellcheck source=/dev/null
    source "$VENV_PATH/bin/activate" || {
        log "ERROR" "Failed to activate virtual environment"
        return 1
    }
    
    # Verify Python executable
    if ! "$VENV_PATH/bin/python3" --version >/dev/null 2>&1; then
        log "ERROR" "Python executable not working in virtual environment"
        return 1
    fi
    
    log "INFO" "Virtual environment activated successfully"
    return 0
}

# Enhanced page number input with better error handling
get_page_number() {
    local default_page="${1:-1}"
    
    log "DEBUG" "Requesting page number from user (default: $default_page)"
    
    local page_number
    page_number=$(osascript <<EOF 2>/dev/null || echo "$default_page"
try
    set pageNumber to text returned of (display dialog "Enter starting page number:" default answer "$default_page" buttons {"Cancel", "OK"} default button "OK" giving up after 30)
    return pageNumber
on error
    return "$default_page"
end try
EOF
)
    
    echo "$page_number"
}

# Help and usage information
show_help() {
    cat << EOF
$SCRIPT_NAME v$SCRIPT_VERSION - Extract and summarize PDF annotations

USAGE:
    $0 [OPTIONS] PDF_FILE [PAGE_NUMBER]

ARGUMENTS:
    PDF_FILE        Path to the PDF file to process
    PAGE_NUMBER     Starting page number (optional)

OPTIONS:
    -v, --verbose   Enable verbose output (DEBUG level)
    -h, --help      Show this help message
    --version       Show version information

ENVIRONMENT VARIABLES:
    OPENAI_API_KEY  Required: Your OpenAI API key

EXAMPLES:
    $0 document.pdf
    $0 --verbose document.pdf 5
    $0 -h

EOF
}

# Command line argument parsing
parse_arguments() {
    local args=()
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                LOG_LEVEL="DEBUG"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            --version)
                echo "$SCRIPT_NAME v$SCRIPT_VERSION"
                exit 0
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                show_help >&2
                exit 1
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done
    
    # Process positional arguments
    if [[ ${#args[@]} -eq 0 ]]; then
        log "ERROR" "PDF file argument is required"
        show_help >&2
        exit 1
    fi
    
    INPUT_FILE="${args[0]}"
    if [[ ${#args[@]} -gt 1 ]]; then
        PAGE_NUMBER="${args[1]}"
    fi
}

# Main execution function
main() {
    # Initialize logging
    setup_logging
    log "INFO" "Starting $SCRIPT_NAME v$SCRIPT_VERSION"
    log "DEBUG" "Script directory: $SCRIPT_DIR"
    log "DEBUG" "Configuration: VENV_PATH=$VENV_PATH, SCRIPT_PATH=$SCRIPT_PATH"
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Validate environment and inputs
    log "INFO" "Validating environment and inputs..."
    check_environment || exit 1
    validate_input_file "$INPUT_FILE" || exit 1
    
    # Handle page number input
    if [[ -z "$PAGE_NUMBER" ]]; then
        PAGE_NUMBER=$(get_page_number)
        log "DEBUG" "Received page number from user: $PAGE_NUMBER"
    fi
    
    validate_page_number "$PAGE_NUMBER" || exit 1
    
    # Setup virtual environment
    log "INFO" "Setting up Python virtual environment..."
    setup_virtual_environment || exit 1
    
    # Verify Python script exists
    if [[ ! -f "$SCRIPT_PATH" ]]; then
        log "ERROR" "Python script not found: $SCRIPT_PATH"
        exit 1
    fi
    
    # Prepare Python script arguments
    local python_args=("$INPUT_FILE")
    if [[ -n "$PAGE_NUMBER" && "$PAGE_NUMBER" != "1" ]]; then
        python_args+=("--start-page" "$PAGE_NUMBER")
    fi
    
    # Execute Python script
    log "INFO" "Executing Python script with arguments: ${python_args[*]}"
    
    # Export the API key for the Python script
    export OPENAI_API_KEY
    
    if ! "$VENV_PATH/bin/python3" "$SCRIPT_PATH" "${python_args[@]}" 2>&1 | while IFS= read -r line; do
        log "INFO" "Python: $line"
        echo "$line"
    done; then
        log "ERROR" "Python script execution failed"
        exit 1
    fi
    
    log "INFO" "Script completed successfully"
    log "INFO" "Log file saved to: $LOG_FILE"
    
    # Show completion dialog
    osascript -e 'display notification "PDF annotation extraction completed successfully!" with title "PDFExtractor"' 2>/dev/null || true
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
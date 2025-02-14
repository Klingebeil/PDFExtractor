#!/bin/zsh
# Make sure to edit this line above to your virtual environment

# Path to output directory for debugging (can be deleted if not necessary)
output_dir=~/PDFExtractor

# Create output directory if it doesn't exist
mkdir -p "$output_dir"

# Log the start of the script and current working directory
echo "Starting script..." > "$output_dir/quick_action_log.txt"
echo "Current directory: $(pwd)" >> "$output_dir/quick_action_log.txt"
echo "Script path: $0" >> "$output_dir/quick_action_log.txt"
echo "Arguments: $@" >> "$output_dir/quick_action_log.txt"

# Define the function to get page number using AppleScript
get_page_number() {
    osascript <<EOF
        set pageNumber to text returned of (display dialog "Enter starting page number (leave empty for default: 1):" default answer "1" buttons {"Cancel", "OK"} default button "OK")
        return pageNumber
EOF
}

# Log the start of the script and current working directory (can be deleted if not necessary)
echo "Starting script..." > "$output_dir/quick_action_log.txt"
echo "Current directory: $(pwd)" >> "$output_dir/quick_action_log.txt"
echo "Script path: $0" >> "$output_dir/quick_action_log.txt"
echo "Arguments: $@" >> "$output_dir/quick_action_log.txt"

# Define paths
VENV_PATH="/Users/johannesklingebieljohannesklingebiel/Library/Scripts/PDFExtractor/venv"
SCRIPT_PATH="/Users/johannesklingebieljohannesklingebiel/Library/Scripts/PDFExtractor/extract_annotations.py"

# Check paths
echo "VENV Path: $VENV_PATH" >> "$output_dir/quick_action_log.txt"
echo "Script Path: $SCRIPT_PATH" >> "$output_dir/quick_action_log.txt"

# Get page number from user (store it to prevent multiple calls)
echo "About to get page number..." >> "$output_dir/quick_action_log.txt"
if [[ -z "$2" ]]; then
    PAGE_NUMBER=$(get_page_number)
else
    PAGE_NUMBER="$2"
fi
echo "Received page number: $PAGE_NUMBER" >> "$output_dir/quick_action_log.txt"

# Activate the virtual environment
source "$VENV_PATH/bin/activate" || { echo "Failed to activate virtual environment" >> "$output_dir/quick_action_log.txt"; exit 1; }

# Run the Python script with the provided argument
if [[ -n "$PAGE_NUMBER" && "$PAGE_NUMBER" =~ ^[0-9]+$ ]]; then
    echo "Running Python script with page number $PAGE_NUMBER" >> "$output_dir/quick_action_log.txt"
    "$VENV_PATH/bin/python3" "$SCRIPT_PATH" "$1" --start-page "$PAGE_NUMBER" >> "$output_dir/quick_action_log.txt" 2>&1
else
    echo "Running Python script without page number" >> "$output_dir/quick_action_log.txt"
    "$VENV_PATH/bin/python3" "$SCRIPT_PATH" "$1" >> "$output_dir/quick_action_log.txt" 2>&1
fi

# Log the script completion
echo "Script finished: $(date)" >> "$output_dir/quick_action_log.txt"

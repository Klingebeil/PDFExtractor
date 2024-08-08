#!/bin/zsh
# Make sure to edit this line above to your virtual environment

# Path to output directory for debugging (can be deleted if not necessary)
output_dir=~/PDFExtractor

# Create output directory if it doesn't exist (can be deleted if not necessary)
mkdir -p "$output_dir"

# Log the start of the script and current working directory (can be deleted if not necessary)
echo "Starting script..." > "$output_dir/quick_action_log.txt"
echo "Current directory: $(pwd)" >> "$output_dir/quick_action_log.txt"
echo "Script path: $0" >> "$output_dir/quick_action_log.txt"
echo "Arguments: $@" >> "$output_dir/quick_action_log.txt"

# Define paths
VENV_PATH="<YOURPATH>/PDFExtractor/venv"
SCRIPT_PATH="<YOURPATH>/PDFExtractor/extract_annotations.py"

# Check paths
echo "VENV Path: $VENV_PATH" >> "$output_dir/quick_action_log.txt"
echo "Script Path: $SCRIPT_PATH" >> "$output_dir/quick_action_log.txt"

# Activate the virtual environment
source "$VENV_PATH/bin/activate" || { echo "Failed to activate virtual environment" >> "$output_dir/quick_action_log.txt"; exit 1; }

# Run the Python script with the provided argument
"$VENV_PATH/bin/python3" "$SCRIPT_PATH" "$1" >> "$output_dir/quick_action_log.txt" 2>&1

# Log the script completion (can be deleted if not necessary)
echo "Script finished." >> "$output_dir/quick_action_log.txt"
#!/bin/bash

# Simple .env setup script for PDFExtractor
# This creates a .env file safely without risk of committing to git

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
EXAMPLE_FILE="$SCRIPT_DIR/.env.example"

echo "🔐 PDFExtractor - Secure .env Setup"
echo "==================================="
echo ""

# Check for API key as parameter
if [[ $# -gt 0 ]]; then
    API_KEY="$1"
    echo "✅ Using API key from command line parameter"
else
    # Check if .env already exists
    if [[ -f "$ENV_FILE" ]]; then
        echo "⚠️  .env file already exists!"
        read -p "Do you want to overwrite it? (y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            echo "Setup cancelled."
            exit 0
        fi
    fi

    # Check if .env.example exists
    if [[ ! -f "$EXAMPLE_FILE" ]]; then
        echo "❌ Error: .env.example not found!"
        echo "Please run this script from the PDFExtractor directory."
        exit 1
    fi

    echo "📋 Instructions:"
    echo "1. Get your OpenAI API key from: https://platform.openai.com/api-keys"
    echo "2. Your API key should start with 'sk-'"
    echo "3. The .env file is automatically ignored by git"
    echo "4. You can paste your key (it will be visible, but that's OK - this is your local machine)"
    echo ""
    echo "💡 Alternative: Run './setup_env.sh YOUR_API_KEY' to set it directly"
    echo ""

    # Prompt for API key (without -s so pasting works)
    echo "🔑 Please paste your OpenAI API key below:"
    echo "   (Tip: Copy your key, then paste it here with Cmd+V)"
    read -p "API Key: " API_KEY
fi

# Basic validation
if [[ -z "$API_KEY" ]]; then
    echo "❌ No API key provided. Setup cancelled."
    exit 1
fi

if [[ ! "$API_KEY" =~ ^sk-[a-zA-Z0-9\-_]{20,}$ ]]; then
    echo "⚠️  API key format seems unusual (should start with 'sk-')"
    read -p "Continue anyway? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

# Create .env file
cat > "$ENV_FILE" << EOF
# PDFExtractor Environment Variables
# This file is gitignored - safe to store secrets here

# OpenAI API Key
OPENAI_API_KEY=$API_KEY

# Optional: Uncomment and modify as needed
# LOG_LEVEL=INFO
EOF

# Set restrictive permissions
chmod 600 "$ENV_FILE"

echo ""
echo "✅ Success! .env file created with secure permissions"
echo "🔒 File permissions set to 600 (owner read/write only)"
echo "🙈 This file is gitignored and won't be committed"
echo ""
echo "🚀 Your PDFExtractor is now ready to use with Apple Automator!"
echo ""
echo "Quick test: Run './run_python_script.sh --help' to verify setup"
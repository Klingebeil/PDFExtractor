#!/bin/bash

# Git setup script for PDFExtractor repository
# This script will connect your local directory to the GitHub repository

echo "🚀 Setting up PDFExtractor GitHub repository..."

# Initialize git if not already initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing git repository..."
    git init
fi

# Set up remote (replace with your actual repository URL)
echo "🔗 Adding remote repository..."
git remote remove origin 2>/dev/null || true  # Remove existing origin if any
git remote add origin https://github.com/Klingebeil/PDFExtractor.git

# Set up git configuration (update with your details)
echo "⚙️ Setting up git configuration..."
git config user.name "Klingebeil"
git config user.email "your-email@example.com"  # Update this with your email

# Stage all files
echo "📦 Staging files..."
git add .

# Commit changes
echo "💾 Creating initial commit..."
git commit -m "Initial release v1.1.0

✨ Features:
- Concurrent PDF annotation extraction
- AI-powered summarization with OpenAI GPT-4
- Smart caching and rate limiting
- Robust error handling with retry logic
- Cross-platform shell script launcher
- External YAML configuration
- Professional logging system
- Security improvements

🔧 Technical improvements:
- Multi-threaded page processing
- Environment variable API key handling
- Dynamic path detection
- Comprehensive input validation
- Command-line argument parsing
- Structured logging with multiple severity levels"

# Set main branch
echo "🌟 Setting main branch..."
git branch -M main

# Push to GitHub
echo "⬆️ Pushing to GitHub..."
echo "Note: You may be prompted for GitHub authentication"
git push -u origin main --force

echo "✅ Repository setup complete!"
echo ""
echo "🌐 Your repository is now available at:"
echo "   https://github.com/Klingebeil/PDFExtractor"
echo ""
echo "📋 Next steps:"
echo "   1. Update the email in git config: git config user.email 'your-email@example.com'"
echo "   2. Review the README.md file on GitHub"
echo "   3. Add any additional documentation"
echo "   4. Consider creating GitHub releases for version tracking"
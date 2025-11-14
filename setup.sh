#!/bin/bash

# Firecrawl Crawler Setup Script
# Prerequisites: Firecrawl already running at http://localhost:3002

set -e  # Exit on error

echo "🔥 Firecrawl Crawler Setup"
echo "=========================="
echo ""

# Check Python version
echo "📋 Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Found Python $PYTHON_VERSION"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip"
    exit 1
fi
echo "✅ Found pip3"

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt
echo "✅ Dependencies installed"

# Create .env file if it doesn't exist
echo ""
if [ -f .env ]; then
    echo "✅ .env file already exists"
else
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# Firecrawl Configuration
FIRECRAWL_API_URL=http://localhost:3002

# Output directory
OUTPUT_DIR=./output
EOF
    echo "✅ Created .env file (edit it to customize)"
fi

# Create output directory
echo ""
echo "📁 Creating output directory..."
mkdir -p output
echo "✅ Output directory created"

# Test the installation
echo ""
echo "🧪 Testing setup..."
echo "Checking Python imports..."
python3 -c "import requests; import os; from dotenv import load_dotenv; print('✅ All dependencies imported successfully')" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Setup validation passed!"
else
    echo "⚠️  Some imports failed, but you can still try running the crawler"
fi

# Summary
echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📝 Configuration:"
echo "  - Python version: $PYTHON_VERSION"
echo "  - Dependencies: installed"
echo "  - Output directory: ./output"
echo "  - Config file: .env (edit if needed)"
echo ""
echo "🚀 Ready to crawl!"
echo ""
echo "Quick start commands:"
echo "  1. List sections:    python3 crawl_sections.py list"
echo "  2. Test scrape:      python3 main.py scrape https://example.com"
echo "  3. Crawl a section:  python3 crawl_sections.py crawl graduate_school"
echo ""
echo "📖 Full documentation: See README.md"
echo ""

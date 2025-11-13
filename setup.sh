#!/bin/bash

# Firecrawl Crawler Setup Script
# This script helps you set up the crawler on a new machine

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

# Check for Firecrawl
echo ""
echo "🔍 Checking for Firecrawl..."
if curl -s http://localhost:3002/health > /dev/null 2>&1; then
    echo "✅ Firecrawl is running at http://localhost:3002"
else
    echo "⚠️  Firecrawl is not running at http://localhost:3002"
    echo ""
    echo "Please start Firecrawl:"
    echo "  Option 1 (Docker): docker-compose up -d"
    echo "  Option 2 (npm):    firecrawl start"
    echo "  Option 3 (Cloud):  Use https://api.firecrawl.dev with API key"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create .env file if it doesn't exist
echo ""
if [ -f .env ]; then
    echo "✅ .env file already exists"
else
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# Firecrawl Configuration
FIRECRAWL_API_URL=http://localhost:3002

# For Firecrawl Cloud, uncomment and add your API key:
# FIRECRAWL_API_URL=https://api.firecrawl.dev
# FIRECRAWL_API_KEY=your_api_key_here

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
echo "🧪 Testing installation..."
if python3 main.py scrape https://example.com --output ./output/test 2>/dev/null; then
    echo "✅ Test scrape successful!"
    rm -rf ./output/test
else
    echo "⚠️  Test scrape failed (may need Firecrawl running)"
fi

# Summary
echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo "1. Edit .env file if needed (for custom API URL or key)"
echo "2. Edit sections_config.json to define your sections"
echo "3. Run your first crawl:"
echo "   python3 main.py scrape https://example.com"
echo "   python3 crawl_sections.py list"
echo ""
echo "Documentation: See README.md for full usage guide"
echo ""


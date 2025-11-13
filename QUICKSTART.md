# Quick Start Guide

Get up and running in 5 minutes!

## Step 1: Install Firecrawl (Choose One)

### Option A: Docker (Easiest)
```bash
git clone https://github.com/mendableai/firecrawl.git
cd firecrawl
docker-compose up -d
```

### Option B: NPM
```bash
npm install -g firecrawl
firecrawl start
```

### Option C: Use Cloud
Sign up at [firecrawl.dev](https://firecrawl.dev) and get an API key.

## Step 2: Install This Crawler

```bash
# Clone the repo
git clone <your-repo-url>
cd firecrawl-crawler

# Run setup script
./setup.sh

# Or manually:
pip install -r requirements.txt
```

## Step 3: Configure (Optional)

Edit `.env` file:
```bash
# For local Firecrawl
FIRECRAWL_API_URL=http://localhost:3002

# For Firecrawl Cloud
FIRECRAWL_API_URL=https://api.firecrawl.dev
FIRECRAWL_API_KEY=your_key_here
```

## Step 4: Test It

```bash
# Scrape a single page
python main.py scrape https://example.com

# Check the output
ls output/
cat output/Example-Domain.md
```

## Step 5: Crawl Your First Site

```bash
# Crawl a documentation site
python main.py crawl https://docs.example.com --max-depth 2 --limit 50

# Or use section-based crawling
python crawl_sections.py list
python crawl_sections.py crawl documentation
```

## Common Use Cases

### Use Case 1: Documentation Site
```bash
# Initial crawl
python main.py crawl https://docs.example.com --max-depth 3 --limit 200 --output ./output/docs

# Weekly updates
python main.py update https://docs.example.com --auto-update
```

### Use Case 2: Multiple Sections
```bash
# Configure sections in sections_config.json
{
  "sections": {
    "docs": {
      "url": "https://example.com/docs/",
      "output_dir": "output/docs",
      "max_depth": 3,
      "limit": 200
    },
    "blog": {
      "url": "https://example.com/blog/",
      "output_dir": "output/blog",
      "max_depth": 2,
      "limit": 50
    }
  }
}

# Crawl all sections
python crawl_sections.py crawl docs
python crawl_sections.py crawl blog
```

### Use Case 3: RAG System
```python
# Load into your RAG system
from pathlib import Path

# Load all docs
for file in Path("output/docs/").glob("*.md"):
    content = file.read_text()
    # Add to vector database
    vectordb.add_document(content)
```

## Next Steps

- Read [README.md](README.md) for full documentation
- Configure [sections_config.json](sections_config.json) for your needs
- Set up cron jobs for automated updates
- Integrate with your RAG system

## Need Help?

- Check [Troubleshooting](README.md#troubleshooting) section
- See [API Reference](README.md#api-reference)
- Review [Firecrawl docs](https://docs.firecrawl.dev)


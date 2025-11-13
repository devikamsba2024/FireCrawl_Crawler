# Firecrawl Crawler

A Python client for scraping websites using Firecrawl and saving content as markdown files. Designed for building RAG (Retrieval-Augmented Generation) knowledge bases with organized, updateable content.

## 🌟 Features

- 🌐 **Scrape single URLs** or **crawl entire websites**
- 📝 Save scraped content as **clean markdown files**
- 📁 **Section-based organization** with independent folders and metadata
- 🔄 **Incremental updates** - detect and re-scrape only changed pages
- 🗺️ **Sitemap-based change detection**
- 🎯 **Perfect for RAG systems** - organized, chunked content ready for embeddings
- ⚙️ Configurable crawl depth, page limits, and update schedules
- 📊 Automatic index generation for each section
- 🔧 CLI tools for easy management

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Section-Based Crawling](#section-based-crawling)
- [Configuration](#configuration)
- [Incremental Updates](#incremental-updates)
- [For RAG Systems](#for-rag-systems)
- [Scheduling with Cron](#scheduling-with-cron)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### 1. Python 3.7+
```bash
python3 --version
```

### 2. Firecrawl Instance

You need a running Firecrawl instance (local or cloud).

#### Option A: Local Firecrawl (Recommended for Development)

**Using Docker:**
```bash
# Clone Firecrawl
git clone https://github.com/mendableai/firecrawl.git
cd firecrawl

# Start with Docker Compose
docker-compose up -d

# Verify it's running
curl http://localhost:3002/health
```

**Using npm:**
```bash
# Install Firecrawl
npm install -g firecrawl

# Start the server
firecrawl start

# Verify it's running
curl http://localhost:3002/health
```

#### Option B: Firecrawl Cloud

Sign up at [firecrawl.dev](https://firecrawl.dev) and get an API key.

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd firecrawl-crawler
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Requirements:**
- `requests>=2.32.3`
- `python-dotenv>=1.0.1`

### 3. Configure Environment (Optional)

Create a `.env` file in the project root:

```bash
# For local Firecrawl
FIRECRAWL_API_URL=http://localhost:3002

# For Firecrawl Cloud
FIRECRAWL_API_URL=https://api.firecrawl.dev
FIRECRAWL_API_KEY=your_api_key_here

# Output directory
OUTPUT_DIR=./output
```

## Quick Start

### Test the Installation

```bash
# Check Firecrawl is accessible
curl http://localhost:3002/health

# Test scraping a single page
python main.py scrape https://example.com

# Check the output
ls output/
```

### Your First Crawl

```bash
# Crawl a website section
python main.py crawl https://example.com/docs/ --max-depth 2 --limit 20

# Output will be in ./output/
```

## Usage

### Basic Commands

#### Scrape a Single URL

```bash
python main.py scrape https://example.com
```

**Options:**
- `--full-content`: Include all content (default: only main content)
- `--wait-for MS`: Wait for page load (milliseconds)
- `--output DIR`: Output directory (default: ./output)

#### Crawl an Entire Website

```bash
python main.py crawl https://example.com --max-depth 3 --limit 50
```

**Options:**
- `--max-depth N`: Maximum crawl depth (default: 2)
- `--limit N`: Maximum number of pages (default: 10)
- `--full-content`: Include all content
- `--timeout SECONDS`: Maximum wait time (default: 300)
- `--output DIR`: Output directory

### Examples

```bash
# Scrape with custom output directory
python main.py scrape https://example.com --output ./my-docs

# Crawl documentation site
python main.py crawl https://docs.example.com --max-depth 3 --limit 100

# Use custom Firecrawl instance
python main.py scrape https://example.com --api-url http://localhost:3002

# Use Firecrawl Cloud with API key
python main.py scrape https://example.com --api-url https://api.firecrawl.dev --api-key your_key
```

## Section-Based Crawling

For better organization, use section-based crawling to keep different parts of a website in separate folders with independent metadata.

### Configuration

Edit `sections_config.json` to define your sections:

```json
{
  "sections": {
    "documentation": {
      "name": "Documentation",
      "url": "https://example.com/docs/",
      "output_dir": "output/documentation",
      "max_depth": 3,
      "limit": 200,
      "schedule": "weekly",
      "description": "Product documentation"
    },
    "blog": {
      "name": "Blog",
      "url": "https://example.com/blog/",
      "output_dir": "output/blog",
      "max_depth": 2,
      "limit": 50,
      "schedule": "daily",
      "description": "Company blog posts"
    }
  }
}
```

### Section Commands

```bash
# List all configured sections
python crawl_sections.py list

# Crawl a specific section
python crawl_sections.py crawl documentation

# Crawl all sections
python crawl_sections.py crawl-all

# Check for updates in a section
python crawl_sections.py update documentation --show-urls

# Auto-update changed pages in a section
python crawl_sections.py update documentation --auto-update
```

### Output Structure

```
output/
├── documentation/
│   ├── .scrape_metadata.json    ← Tracks only documentation pages
│   ├── INDEX.md                  ← Table of contents
│   └── *.md files                ← Individual pages
├── blog/
│   ├── .scrape_metadata.json    ← Tracks only blog pages
│   ├── INDEX.md
│   └── *.md files
└── api/
    ├── .scrape_metadata.json
    ├── INDEX.md
    └── *.md files
```

## Configuration

### Command-Line Arguments

All configuration can be set via CLI (highest priority):

```bash
python main.py crawl https://example.com \
  --api-url http://localhost:3002 \
  --api-key your_key \
  --output ./output \
  --max-depth 3 \
  --limit 100
```

### Environment Variables

Set in `.env` file or system environment:

```bash
FIRECRAWL_API_URL=http://localhost:3002
FIRECRAWL_API_KEY=your_api_key
OUTPUT_DIR=./output
```

### Default Values

- API URL: `http://localhost:3002`
- Output: `./output`
- Max Depth: `2`
- Limit: `10`

## Incremental Updates

The crawler tracks when each page was scraped and can detect changes using sitemaps.

### How It Works

1. **Initial Crawl:** Saves `.scrape_metadata.json` with URLs and timestamps
2. **Check Updates:** Compares sitemap `<lastmod>` dates with your timestamps
3. **Smart Re-scraping:** Only re-scrapes pages that have changed

### Update Commands

```bash
# Check which pages changed
python main.py update https://example.com --show-urls

# Automatically update changed pages
python main.py update https://example.com --auto-update

# Update a specific section
python crawl_sections.py update documentation --auto-update
```

### Workflow

```bash
# Day 1: Initial crawl
python crawl_sections.py crawl documentation
# → Saves 100 pages + metadata

# Day 7: Check for updates
python crawl_sections.py update documentation --show-urls
# → Shows: "5 out of 100 pages need updating"

# Day 7: Update only changed pages
python crawl_sections.py update documentation --auto-update
# → Re-scrapes only 5 changed pages (saves time!)
```

## For RAG Systems

This crawler is optimized for RAG (Retrieval-Augmented Generation) workflows.

### Why This Format Works

- ✅ **One file per page** = Natural semantic chunks
- ✅ **Clean markdown** = Better embeddings (no HTML noise)
- ✅ **Source URLs** = Easy citation and attribution
- ✅ **Section folders** = Load only relevant content
- ✅ **Metadata tracking** = Keep embeddings up-to-date

### Loading into Vector Database

**Example with LangChain:**

```python
from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

# Load all markdown files
loader = DirectoryLoader(
    'output/documentation', 
    glob="**/*.md", 
    exclude=["INDEX.md"]
)
documents = loader.load()

# Split by headers for semantic chunks
splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("##", "section")]
)
chunks = splitter.split_documents(documents)

# Create embeddings and store
embeddings = OpenAIEmbeddings()
vectordb = Chroma.from_documents(chunks, embeddings)
```

**Example with Custom Code:**

```python
from pathlib import Path
import json

# Load specific section
section_dir = Path("output/documentation")

for file in section_dir.glob("*.md"):
    if file.name == "INDEX.md":
        continue
    
    # Read content
    content = file.read_text()
    
    # Extract metadata from header
    lines = content.split('\n')
    title = lines[0].replace('# ', '')
    source_url = lines[2].replace('**Source:** ', '')
    
    # Get scrape metadata
    metadata_file = section_dir / ".scrape_metadata.json"
    metadata = json.loads(metadata_file.read_text())
    
    # Process and embed
    # ... your RAG pipeline here
```

### Selective Loading

```python
# Load only specific sections
sections = ["documentation", "api_reference"]
for section in sections:
    files = Path(f"output/{section}/").glob("*.md")
    # Process files
```

## Scheduling with Cron

Automate updates with cron jobs for different sections.

### Example Cron Jobs

```bash
# Edit crontab
crontab -e

# Add these lines:

# Documentation - daily at 2 AM
0 2 * * * cd /path/to/firecrawl-crawler && /usr/bin/python3 crawl_sections.py update documentation --auto-update >> /var/log/crawler.log 2>&1

# Blog - every 6 hours
0 */6 * * * cd /path/to/firecrawl-crawler && /usr/bin/python3 crawl_sections.py update blog --auto-update >> /var/log/crawler.log 2>&1

# API docs - weekly on Monday at 3 AM
0 3 * * 1 cd /path/to/firecrawl-crawler && /usr/bin/python3 crawl_sections.py update api_reference --auto-update >> /var/log/crawler.log 2>&1

# Full re-crawl - monthly on 1st at 4 AM
0 4 1 * * cd /path/to/firecrawl-crawler && /usr/bin/python3 crawl_sections.py crawl-all >> /var/log/crawler.log 2>&1
```

### Cron Schedule Reference

```
* * * * *
│ │ │ │ │
│ │ │ │ └─ Day of week (0-7, Sunday=0 or 7)
│ │ │ └─── Month (1-12)
│ │ └───── Day of month (1-31)
│ └─────── Hour (0-23)
└───────── Minute (0-59)
```

## Project Structure

```
firecrawl-crawler/
├── firecrawl_crawler/          # Main package
│   ├── __init__.py             # Package initialization
│   ├── api.py                  # Firecrawl API client
│   ├── config.py               # Configuration management
│   ├── storage.py              # Markdown storage with metadata
│   ├── sitemap.py              # Sitemap parsing for updates
│   └── utils.py                # Utility functions
├── main.py                     # CLI for basic scraping/crawling
├── crawl_sections.py           # CLI for section-based management
├── sections_config.json        # Section definitions
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
├── README.md                   # This file
└── output/                     # Output directory (created automatically)
    ├── section1/
    │   ├── .scrape_metadata.json
    │   ├── INDEX.md
    │   └── *.md
    └── section2/
        ├── .scrape_metadata.json
        ├── INDEX.md
        └── *.md
```

## API Reference

### FirecrawlClient

```python
from firecrawl_crawler import Config, FirecrawlClient

# Initialize
config = Config(api_url="http://localhost:3002")
client = FirecrawlClient(config)

# Scrape single URL
data = client.scrape_url("https://example.com")

# Crawl website
job_id = client.crawl_website(
    url="https://example.com",
    max_depth=2,
    limit=10
)
result = client.wait_for_crawl(job_id)
```

### MarkdownStorage

```python
from firecrawl_crawler import MarkdownStorage

# Initialize
storage = MarkdownStorage(output_dir="./output")

# Save single page
storage.save_single_page(scraped_data)

# Save multiple pages with index
storage.save_multiple_pages(pages_list, create_index=True)

# Get previously scraped URLs
urls = storage.get_scraped_urls()

# Get page metadata
info = storage.get_page_info("https://example.com")
```

### SitemapParser

```python
from firecrawl_crawler import SitemapParser

# Initialize
sitemap = SitemapParser("https://example.com")

# Get all URLs
urls = sitemap.get_all_urls()

# Find updated URLs
updated = sitemap.get_updated_urls(
    scraped_urls=storage.metadata["pages"],
    path_filter="/docs/"
)
```

## Troubleshooting

### Firecrawl Connection Error

**Error:** `Connection refused` or `Could not connect to Firecrawl`

**Solution:**
```bash
# Check if Firecrawl is running
curl http://localhost:3002/health

# If not running, start it:
cd /path/to/firecrawl
docker-compose up -d

# Or with npm:
firecrawl start
```

### Module Import Errors

**Error:** `ModuleNotFoundError: No module named 'requests'`

**Solution:**
```bash
pip install -r requirements.txt
```

### Permission Errors

**Error:** `Permission denied` when saving files

**Solution:**
```bash
# Check output directory permissions
ls -la output/

# Fix permissions
chmod -R 755 output/
```

### Update Detection Not Working

**Problem:** `update` command says no changes, but you know pages changed

**Solutions:**
1. Check sitemap exists: `curl https://example.com/sitemap.xml`
2. Verify metadata file: `ls output/section/.scrape_metadata.json`
3. Check base URL matches: URLs in metadata should match sitemap
4. Try manual re-crawl: `python crawl_sections.py crawl section`

### Crawl Timeout

**Error:** `Crawl job timed out`

**Solutions:**
```bash
# Increase timeout
python main.py crawl https://example.com --timeout 600

# Or reduce scope
python main.py crawl https://example.com --limit 50 --max-depth 2
```

### Empty Markdown Files

**Problem:** Files are created but have no content

**Solutions:**
1. Check if Firecrawl can access the website
2. Try with `--full-content` flag
3. Increase `--wait-for` for JavaScript-heavy sites:
   ```bash
   python main.py scrape https://example.com --wait-for 3000
   ```

## Advanced Usage

### Custom Section Configuration

Create multiple config files for different projects:

```bash
# Project 1
python crawl_sections.py --config project1_sections.json crawl docs

# Project 2
python crawl_sections.py --config project2_sections.json crawl docs
```

### Parallel Crawling

Crawl multiple sections simultaneously:

```bash
# Terminal 1
python crawl_sections.py crawl documentation

# Terminal 2
python crawl_sections.py crawl blog

# Terminal 3
python crawl_sections.py crawl api_reference
```

### Integration with CI/CD

```yaml
# .github/workflows/update-docs.yml
name: Update Documentation

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Update documentation
        env:
          FIRECRAWL_API_URL: ${{ secrets.FIRECRAWL_API_URL }}
          FIRECRAWL_API_KEY: ${{ secrets.FIRECRAWL_API_KEY }}
        run: |
          python crawl_sections.py update documentation --auto-update
      
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add output/
          git commit -m "Update documentation" || exit 0
          git push
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - feel free to use this project however you'd like!

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review [Firecrawl documentation](https://docs.firecrawl.dev)
- Open an issue on GitHub

---

**Built for RAG systems** 🔥 **Powered by Firecrawl** 🚀

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

## 📋 Prerequisites

- **Python 3.7+**
- **Firecrawl running** at `http://localhost:3002` (or cloud instance)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/devikamsba2024/FireCrawl_Crawler.git
cd FireCrawl_Crawler
```

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

Or use the automated setup:
```bash
./setup.sh
```

### 3. Verify Firecrawl Connection

```bash
curl http://localhost:3002/health
```

Should return: `{"status":"ok"}`

### 4. Test the Crawler

```bash
# Scrape a single page
python3 main.py scrape https://example.com

# Check the output
ls output/
cat output/Example-Domain.md
```

## 📖 Usage

### Basic Commands

#### Scrape a Single Page
```bash
python3 main.py scrape https://www.wichita.edu/academics/graduate_school/
```

**Options:**
- `--output DIR`: Output directory (default: `./output`)
- `--full-content`: Include all content (default: only main content)
- `--wait-for MS`: Wait for page load (milliseconds)

#### Crawl Multiple Pages
```bash
python3 main.py crawl https://www.wichita.edu/academics/graduate_school/ --max-depth 3 --limit 50
```

**Options:**
- `--max-depth N`: Maximum crawl depth (default: 2)
- `--limit N`: Maximum number of pages (default: 10)
- `--timeout SECONDS`: Maximum wait time (default: 300)
- `--output DIR`: Output directory

#### Check for Updates
```bash
# Show which pages have changed
python3 main.py update https://www.wichita.edu/academics/graduate_school/ --show-urls

# Automatically re-scrape changed pages
python3 main.py update https://www.wichita.edu/academics/graduate_school/ --auto-update
```

### Section-Based Crawling (Recommended)

For better organization, use section-based crawling to manage different website areas independently.

#### List All Sections
```bash
python3 crawl_sections.py list
```

#### Crawl a Specific Section
```bash
python3 crawl_sections.py crawl graduate_school
python3 crawl_sections.py crawl admissions
python3 crawl_sections.py crawl research
```

#### Crawl All Sections
```bash
python3 crawl_sections.py crawl-all
```

#### Update a Section
```bash
# Check for updates
python3 crawl_sections.py update graduate_school --show-urls

# Auto-update changed pages
python3 crawl_sections.py update graduate_school --auto-update
```

### Examples

```bash
# Example 1: Graduate School (27 pages, ~5-10 min)
python3 crawl_sections.py crawl graduate_school

# Example 2: Research Section (100 pages, ~20-30 min)
python3 crawl_sections.py crawl research

# Example 3: Small test crawl
python3 main.py crawl https://www.wichita.edu/about/ --max-depth 2 --limit 20

# Example 4: Check for daily updates
python3 crawl_sections.py update admissions --auto-update
```

## 📁 Output Structure

### Section-Based Organization
```
output/
├── graduate_school/
│   ├── .scrape_metadata.json    ← Tracks scrape times & URLs
│   ├── INDEX.md                  ← Table of contents
│   └── *.md files                ← Individual pages
├── admissions/
│   ├── .scrape_metadata.json
│   ├── INDEX.md
│   └── *.md files
└── research/
    ├── .scrape_metadata.json
    ├── INDEX.md
    └── *.md files
```

### Metadata File Example
```json
{
  "pages": {
    "https://www.wichita.edu/academics/graduate_school/": {
      "file": "output/graduate_school/Graduate-School.md",
      "scraped_at": "2025-11-13T15:35:14.714005",
      "file_size": 3974
    }
  },
  "last_crawl": "2025-11-13T15:35:14"
}
```

### Markdown File Format
Each `.md` file includes:
```markdown
# Page Title

**Source:** https://www.wichita.edu/page

---

[Clean markdown content here...]
```

## ⚙️ Configuration

### Configure Sections

Edit `sections_config.json` to define your website sections:

```json
{
  "sections": {
    "graduate_school": {
      "name": "Graduate School",
      "url": "https://www.wichita.edu/academics/graduate_school/",
      "output_dir": "output/graduate_school",
      "max_depth": 3,
      "limit": 100,
      "schedule": "weekly",
      "description": "Graduate programs and requirements"
    }
  }
}
```

### Environment Variables (Optional)

Create a `.env` file:
```bash
FIRECRAWL_API_URL=http://localhost:3002
OUTPUT_DIR=./output
```

Or use command-line arguments to override:
```bash
python3 main.py scrape https://example.com --api-url http://localhost:3002 --output ./my-output
```

## 🔄 Incremental Updates

The crawler tracks when each page was scraped and uses sitemaps to detect changes.

### How Update Detection Works

1. **Initial Crawl:** Saves metadata with timestamps
   ```json
   {
     "scraped_at": "2025-11-13T15:35:14"
   }
   ```

2. **Check Sitemap:** Fetches website's sitemap.xml
   ```xml
   <lastmod>2025-11-20T14:22:00</lastmod>
   ```

3. **Compare Dates:** If `lastmod > scraped_at` → page needs updating

4. **Re-scrape:** Only downloads changed pages

### Update Workflow

```bash
# Step 1: Initial crawl (Day 1)
python3 crawl_sections.py crawl graduate_school
# → Saves 27 pages + metadata

# Step 2: Check for updates (Day 7)
python3 crawl_sections.py update graduate_school --show-urls
# → Shows: "5 out of 27 pages need updating"

# Step 3: Update only changed pages
python3 crawl_sections.py update graduate_school --auto-update
# → Re-scrapes only 5 changed pages (saves time!)
```

## 🤖 For RAG Systems

### Why This Format is Ideal for RAG

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
from pathlib import Path

# Load all markdown files
loader = DirectoryLoader(
    'output/graduate_school', 
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
# ... your vector database code
```

**Simple Python Example:**
```python
from pathlib import Path
import json

# Load graduate school section
section_dir = Path("output/graduate_school")

for file in section_dir.glob("*.md"):
    if file.name == "INDEX.md":
        continue
    
    # Read content
    content = file.read_text()
    
    # Extract metadata
    lines = content.split('\n')
    title = lines[0].replace('# ', '')
    source_url = lines[2].replace('**Source:** ', '')
    
    # Process for your RAG system
    # add_to_vector_db(content, metadata={"title": title, "url": source_url})
```

**Load Specific Sections:**
```python
# Load multiple sections
sections = ["graduate_school", "admissions", "research"]
for section in sections:
    files = Path(f"output/{section}/").glob("*.md")
    for file in files:
        content = file.read_text()
        # Process content
```

## 📅 Scheduling with Cron

Automate updates with cron jobs.

### Example Cron Jobs

```bash
# Edit crontab
crontab -e
```

Add these lines:
```bash
# Graduate school - weekly on Monday at 2 AM
0 2 * * 1 cd /path/to/FireCrawl_Crawler && python3 crawl_sections.py update graduate_school --auto-update >> /var/log/crawler.log 2>&1

# Admissions - daily at 3 AM
0 3 * * * cd /path/to/FireCrawl_Crawler && python3 crawl_sections.py update admissions --auto-update >> /var/log/crawler.log 2>&1

# Research - monthly on 1st at 4 AM
0 4 1 * * cd /path/to/FireCrawl_Crawler && python3 crawl_sections.py update research --auto-update >> /var/log/crawler.log 2>&1
```

### Cron Schedule Quick Reference
```
* * * * *
│ │ │ │ └─ Day of week (0-7, Sunday=0/7)
│ │ │ └─── Month (1-12)
│ │ └───── Day of month (1-31)
│ └─────── Hour (0-23)
└───────── Minute (0-59)
```

**Common schedules:**
- `0 2 * * *` - Daily at 2 AM
- `0 2 * * 1` - Weekly on Monday at 2 AM
- `0 2 1 * *` - Monthly on 1st at 2 AM
- `0 */6 * * *` - Every 6 hours

## 📊 Project Structure

```
FireCrawl_Crawler/
├── firecrawl_crawler/          # Main package
│   ├── __init__.py             # Package exports
│   ├── api.py                  # Firecrawl API client
│   ├── config.py               # Configuration management
│   ├── storage.py              # Markdown storage + metadata
│   ├── sitemap.py              # Sitemap parser for updates
│   └── utils.py                # Utility functions
├── main.py                     # Basic CLI commands
├── crawl_sections.py           # Section-based management CLI
├── sections_config.json        # Section definitions
├── setup.sh                    # Automated setup script
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
├── README.md                   # This file
├── QUICKSTART.md              # 5-minute guide
└── output/                     # Output directory (auto-created)
```

## 🔧 API Reference

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

# Save multiple pages
storage.save_multiple_pages(pages_list, create_index=True)

# Get scraped URLs
urls = storage.get_scraped_urls()

# Get page info
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
    scraped_urls=storage.metadata["pages"]
)
```

## 🐛 Troubleshooting

### Connection Refused

**Problem:** `Connection refused` when connecting to Firecrawl

**Solution:**
```bash
# Check if Firecrawl is running
curl http://localhost:3002/health

# If not running, restart it
cd /path/to/firecrawl
docker-compose restart
```

### No Pages Found

**Problem:** Crawl completes but finds 0 pages

**Solution:**
```bash
# Test single page first
python3 main.py scrape https://www.wichita.edu

# If that works, try small crawl
python3 main.py crawl https://www.wichita.edu --max-depth 1 --limit 5

# Check Firecrawl logs
docker logs firecrawl
```

### Update Detection Not Working

**Problem:** Update command shows no changes

**Solution:**
1. Check sitemap exists:
   ```bash
   curl https://www.wichita.edu/sitemap.xml
   ```

2. Verify metadata file exists:
   ```bash
   ls output/graduate_school/.scrape_metadata.json
   ```

3. Check timestamps:
   ```bash
   cat output/graduate_school/.scrape_metadata.json | head -20
   ```

### Permission Errors

**Problem:** `Permission denied` when saving files

**Solution:**
```bash
chmod -R 755 output/
mkdir -p output/
```

### Module Not Found

**Problem:** `ModuleNotFoundError: No module named 'requests'`

**Solution:**
```bash
pip3 install -r requirements.txt

# Or manually:
pip3 install requests python-dotenv
```

## 📝 Tips & Best Practices

### For Efficient Crawling

1. **Start small, then expand:**
   ```bash
   # Test with small limit first
   python3 main.py crawl https://example.com --limit 10
   
   # Then increase
   python3 main.py crawl https://example.com --limit 100
   ```

2. **Use sections for organization:**
   - Better than one massive crawl
   - Independent updates
   - Easier to manage

3. **Regular updates:**
   - Set up daily/weekly cron jobs
   - Keeps RAG data fresh
   - Only downloads what changed

4. **Monitor crawls:**
   ```bash
   # Redirect to log file
   python3 crawl_sections.py crawl section >> crawler.log 2>&1
   
   # Watch progress
   tail -f crawler.log
   ```

### For RAG Integration

1. **Load sections selectively:**
   - Load only relevant sections per query
   - Reduces noise, improves accuracy

2. **Use metadata for citations:**
   - Source URLs in each file
   - Easy to attribute responses

3. **Update embeddings regularly:**
   - Run update checks weekly
   - Re-embed only changed pages

4. **Chunk by headers:**
   - Split on `##` headers
   - Better semantic chunks

## 📖 Additional Resources

- **Firecrawl Documentation:** https://docs.firecrawl.dev
- **Repository:** https://github.com/devikamsba2024/FireCrawl_Crawler
- **Issues:** https://github.com/devikamsba2024/FireCrawl_Crawler/issues

## 📄 License

MIT License - free to use for any purpose.

## 🙏 Acknowledgments

Built with [Firecrawl](https://firecrawl.dev) - the best web scraping API.

---

**Ready to crawl?** Start with: `python3 crawl_sections.py list` 🚀

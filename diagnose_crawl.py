#!/usr/bin/env python3
"""
Diagnostic script to check crawl job status and retry fetching data.
Useful for troubleshooting crawls that complete but don't return data.
"""
import argparse
import json
import sys
from pathlib import Path
from firecrawl_crawler import Config, FirecrawlClient, MarkdownStorage
from firecrawl_crawler.logger import get_logger

logger = get_logger(__name__)


def check_job_status(api_url: str, job_id: str, api_key: str = None):
    """Check the status of a crawl job."""
    print(f"\n{'='*80}")
    print(f"Checking Crawl Job Status")
    print(f"{'='*80}")
    print(f"Job ID: {job_id}")
    print(f"API URL: {api_url}")
    
    config = Config(api_url=api_url, api_key=api_key)
    client = FirecrawlClient(config)
    
    try:
        status_data = client.get_crawl_status(job_id)
        
        status = status_data.get("status", "unknown")
        pages = status_data.get("data", [])
        total_pages = status_data.get("total", 0)
        stats = status_data.get("stats", {})
        error = status_data.get("error")
        
        print(f"\nStatus: {status}")
        print(f"Pages in data array: {len(pages)}")
        print(f"Total pages reported: {total_pages}")
        
        if stats:
            print(f"\nStats:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        if error:
            print(f"\n⚠️  Error: {error}")
        
        if pages:
            print(f"\n✓ Found {len(pages)} page(s) in data array!")
            # Show sample pages
            print(f"\nSample pages (first 5):")
            for i, page in enumerate(pages[:5], 1):
                url = page.get("metadata", {}).get("url") or page.get("url", "unknown")
                title = page.get("metadata", {}).get("title", "Untitled")
                print(f"  {i}. {title}")
                print(f"     URL: {url}")
        elif total_pages > 0:
            print(f"\n⚠️  ISSUE: API reports {total_pages} total pages, but data array is empty!")
            print(f"    This indicates a Firecrawl API timing issue.")
            print(f"    The data may be available later or may have been lost.")
        elif total_pages == 0:
            print(f"\n⚠️  API reports 0 total pages.")
            print(f"    This might mean:")
            print(f"    - The crawl found no matching pages")
            print(f"    - The crawl hasn't started yet")
            print(f"    - The crawl failed silently")
        
        # Show full response
        print(f"\n{'='*80}")
        print(f"Full API Response:")
        print(f"{'='*80}")
        print(json.dumps(status_data, indent=2, default=str))
        
        return status_data
        
    except Exception as e:
        print(f"\n✗ Error checking job status: {e}")
        import traceback
        traceback.print_exc()
        return None


def retry_fetch_data(api_url: str, job_id: str, output_dir: str, api_key: str = None, max_retries: int = 10):
    """Retry fetching data from a completed crawl job."""
    print(f"\n{'='*80}")
    print(f"Retrying Data Fetch for Completed Crawl")
    print(f"{'='*80}")
    print(f"Job ID: {job_id}")
    print(f"API URL: {api_url}")
    print(f"Output Directory: {output_dir}")
    print(f"Max Retries: {max_retries}")
    
    config = Config(api_url=api_url, api_key=api_key)
    client = FirecrawlClient(config)
    storage = MarkdownStorage(output_dir)
    
    import time
    
    for attempt in range(1, max_retries + 1):
        print(f"\n{'='*60}")
        print(f"Attempt {attempt}/{max_retries}")
        print(f"{'='*60}")
        
        try:
            status_data = client.get_crawl_status(job_id)
            status = status_data.get("status", "unknown")
            pages = status_data.get("data", [])
            total_pages = status_data.get("total", 0)
            
            print(f"Status: {status}")
            print(f"Pages in data: {len(pages)}")
            print(f"Total reported: {total_pages}")
            
            if pages:
                print(f"\n✓ SUCCESS! Found {len(pages)} page(s)!")
                print("Saving pages...")
                saved_files = storage.save_multiple_pages(pages, create_index=True)
                print(f"\n✓ Successfully saved {len(saved_files)} pages to: {output_dir}")
                return True
            elif status == "completed" and total_pages > 0:
                print(f"\n⚠️  Still no data (API reports {total_pages} pages)")
                if attempt < max_retries:
                    wait_time = 10 * attempt  # Increasing wait time
                    print(f"Waiting {wait_time}s before next retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"\n✗ Max retries reached. Data still not available.")
                    print(f"\nThis might indicate:")
                    print(f"  - The data was lost by the Firecrawl API")
                    print(f"  - Network connectivity issues during the crawl")
                    print(f"  - The crawl failed silently")
                    return False
            elif status == "completed" and total_pages == 0:
                print(f"\n⚠️  Crawl completed with 0 pages")
                print(f"This might mean no pages matched the crawl criteria.")
                return False
            elif status == "scraping":
                print(f"\n⚠️  Crawl is still in 'scraping' status")
                print(f"Waiting 10s before next check...")
                time.sleep(10)
                continue
            elif status == "failed":
                error = status_data.get("error", "Unknown error")
                print(f"\n✗ Crawl failed: {error}")
                return False
            else:
                print(f"\n⚠️  Unexpected status: {status}")
                if attempt < max_retries:
                    wait_time = 10
                    print(f"Waiting {wait_time}s before next retry...")
                    time.sleep(wait_time)
                    continue
                
        except Exception as e:
            print(f"\n✗ Error on attempt {attempt}: {e}")
            if attempt < max_retries:
                wait_time = 10 * attempt
                print(f"Waiting {wait_time}s before next retry...")
                time.sleep(wait_time)
                continue
            else:
                print(f"\n✗ Max retries reached.")
                return False
    
    return False


def diagnose_section(section_key: str, api_url: str = None, api_key: str = None):
    """Diagnose a section by checking its recent crawl job."""
    config_file = Path("sections_config.json")
    if not config_file.exists():
        print(f"Error: sections_config.json not found")
        sys.exit(1)
    
    sections_config = json.loads(config_file.read_text())
    
    if section_key not in sections_config["sections"]:
        print(f"Error: Section '{section_key}' not found")
        sys.exit(1)
    
    section = sections_config["sections"][section_key]
    output_dir = section["output_dir"]
    
    # Check if there's a recent crawl with metadata
    storage = MarkdownStorage(output_dir)
    metadata = storage.metadata
    
    print(f"\n{'='*80}")
    print(f"Diagnosing Section: {section['name']}")
    print(f"{'='*80}")
    print(f"URL: {section['url']}")
    print(f"Output: {output_dir}")
    
    if metadata.get("last_job_id"):
        job_id = metadata["last_job_id"]
        print(f"\nFound last job ID in metadata: {job_id}")
        print(f"\nChecking job status...")
        check_job_status(api_url or "http://localhost:3002", job_id, api_key)
    else:
        print(f"\n⚠️  No job ID found in metadata")
        print(f"This section may not have been crawled yet, or metadata is missing.")
        print(f"\nTo diagnose a specific job, use:")
        print(f"  python3 diagnose_crawl.py check <job_id>")


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose crawl jobs and retry fetching data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check a specific job status
  python3 diagnose_crawl.py check <job_id>
  
  # Retry fetching data for a completed job
  python3 diagnose_crawl.py retry <job_id> --output output/leadership
  
  # Diagnose a section (checks last job from metadata)
  python3 diagnose_crawl.py section leadership
  
  # With custom API URL
  python3 diagnose_crawl.py check <job_id> --api-url http://your-vm-ip:3002
        """
    )
    
    parser.add_argument(
        "--api-url",
        default=None,
        help="Firecrawl API URL (defaults to env var or localhost:3002)"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Firecrawl API key (defaults to env var)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=10,
        help="Maximum retry attempts for retry command (default: 10)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    subparsers.required = True
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check job status")
    check_parser.add_argument("job_id", help="Crawl job ID")
    
    # Retry command
    retry_parser = subparsers.add_parser("retry", help="Retry fetching data for a completed job")
    retry_parser.add_argument("job_id", help="Crawl job ID")
    retry_parser.add_argument("--output", required=True, help="Output directory to save pages")
    
    # Section command
    section_parser = subparsers.add_parser("section", help="Diagnose a section (uses last job from metadata)")
    section_parser.add_argument("section_key", help="Section key (e.g., leadership, innovation)")
    
    args = parser.parse_args()
    
    config = Config(api_url=args.api_url, api_key=args.api_key)
    api_url = config.api_url
    
    if args.command == "check":
        check_job_status(api_url, args.job_id, config.api_key)
    elif args.command == "retry":
        success = retry_fetch_data(api_url, args.job_id, args.output, config.api_key, args.max_retries)
        sys.exit(0 if success else 1)
    elif args.command == "section":
        diagnose_section(args.section_key, api_url, config.api_key)


if __name__ == "__main__":
    main()


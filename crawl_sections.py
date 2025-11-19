#!/usr/bin/env python3
"""
Crawl specific sections of the website independently.
Useful for scheduling different sections with different frequencies.
"""
import argparse
import json
import sys
from pathlib import Path
from firecrawl_crawler import Config, FirecrawlClient, MarkdownStorage
from firecrawl_crawler.logger import get_logger

logger = get_logger(__name__)


def load_sections_config(config_file: str = "sections_config.json"):
    """Load sections configuration."""
    config_path = Path(config_file)
    if not config_path.exists():
        print(f"Error: Config file {config_file} not found")
        sys.exit(1)
    
    return json.loads(config_path.read_text())


def list_sections(sections_config):
    """List all available sections."""
    print("\nAvailable Sections:")
    print("=" * 80)
    
    for key, section in sections_config["sections"].items():
        max_depth = section.get('max_depth', 'auto')
        limit = section.get('limit', 'auto')
        timeout = section.get('timeout', None)
        
        print(f"\n{section['name']} ({key})")
        print(f"  URL: {section['url']}")
        print(f"  Output: {section['output_dir']}")
        timeout_str = str(timeout) + "s" if timeout is not None else "None (no timeout)"
        print(f"  Limits: max_depth={max_depth}, limit={limit}, timeout={timeout_str}")
        if max_depth == 'auto' or limit == 'auto':
            print(f"  ⚠️  Auto-detection: Will analyze sitemap to determine values")
        print(f"  Schedule: {section['schedule']}")
        print(f"  Description: {section['description']}")


def crawl_section(section_key, sections_config, api_url=None, api_key=None, force=False):
    """Crawl a specific section."""
    if section_key not in sections_config["sections"]:
        print(f"Error: Section '{section_key}' not found")
        print(f"Available sections: {', '.join(sections_config['sections'].keys())}")
        sys.exit(1)
    
    section = sections_config["sections"][section_key]
    
    # Auto-detect limit and depth from sitemap if not set
    # Timeout is optional - None means wait indefinitely
    max_depth = section.get('max_depth')
    limit = section.get('limit')
    timeout = section.get('timeout')  # None means no timeout
    
    if max_depth is None or limit is None:
        print(f"\n🔍 Auto-detecting crawl parameters from sitemap...")
        from firecrawl_crawler import SitemapParser
        
        # Parse base URL for sitemap
        from urllib.parse import urlparse
        parsed = urlparse(section['url'])
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        parser = SitemapParser(base_url)
        analysis = parser.analyze_section(section['url'])
        
        if analysis['page_count'] > 0:
            if max_depth is None:
                max_depth = analysis['max_depth']
                print(f"  ✓ Detected max_depth: {max_depth}")
            if limit is None:
                limit = analysis['page_count']
                print(f"  ✓ Detected page count: {limit}")
        else:
            print(f"  ⚠️  No pages found in sitemap, using defaults")
            if max_depth is None:
                max_depth = 2
            if limit is None:
                limit = 50
        print()
    
    print(f"\n{'='*80}")
    print(f"Crawling: {section['name']}")
    print(f"{'='*80}")
    print(f"URL: {section['url']}")
    print(f"Output: {section['output_dir']}")
    print(f"Max Depth: {max_depth}, Limit: {limit}")
    if timeout is None:
        print(f"Timeout: None (wait indefinitely)")
    else:
        print(f"Timeout: {timeout}s ({timeout//60}m {timeout%60}s)")
    print()
    
    # Setup config
    config = Config(
        api_url=api_url,
        api_key=api_key,
        output_dir=section['output_dir']
    )
    
    client = FirecrawlClient(config)
    storage = MarkdownStorage(config.output_dir)
    
    # Check connection before starting
    print(f"Checking API connection to {config.api_url}...")
    if not client.check_connection():
        print(f"\n❌ Error: Cannot connect to Firecrawl API at {config.api_url}")
        print(f"\n💡 Troubleshooting steps:")
        print(f"  1. Verify Firecrawl is running: curl {config.api_url}/health")
        print(f"  2. Check if API URL is correct and accessible from this machine")
        print(f"  3. For VM: Ensure network connectivity and firewall settings")
        print(f"  4. Check if Firecrawl is running on a different host/port")
        sys.exit(1)
    else:
        print(f"✓ API connection successful")
    
    try:
        # Start crawl (use auto-detected values if available)
        job_id = client.crawl_website(
            url=section['url'],
            max_depth=max_depth,
            limit=limit,
            formats=["markdown"],
            only_main_content=True
        )
        
        print(f"Crawl job started: {job_id}")
        print("Waiting for crawl to complete...\n")
        
        # Store job_id in metadata for later retry if needed
        if storage.metadata.get("last_job_id") != job_id:
            storage.metadata["last_job_id"] = job_id
            storage.metadata["last_crawl_url"] = section['url']
            try:
                storage._save_metadata()
                logger.debug(f"Stored job_id {job_id} in metadata for {section_key}")
            except Exception as e:
                logger.warning(f"Could not save job_id to metadata: {e}")
        
        # Wait for completion with configured timeout (already set above)
        # Enable incremental saving so files are saved as they come in
        print("Saving pages incrementally as they are scraped...\n")
        result = client.wait_for_crawl(
            job_id=job_id,
            max_wait_time=timeout,
            poll_interval=5,
            incremental_save=storage  # Pass storage for incremental saving
        )
        
        # Save pages (any that weren't saved incrementally)
        pages = result.get("data", [])
        if pages:
            # Check if we need to save any remaining pages
            saved_urls = set(storage.get_scraped_urls())
            remaining_pages = [
                p for p in pages 
                if (p.get("metadata", {}).get("url") or p.get("url", "unknown")) not in saved_urls
            ]
            
            if remaining_pages:
                print(f"\nCrawl completed! Saving {len(remaining_pages)} remaining pages...")
                saved_files = storage.save_multiple_pages(remaining_pages, create_index=True)
                print(f"\n✓ Successfully saved {len(saved_files)} additional pages to: {config.output_dir}")
            else:
                print(f"\nCrawl completed! All {len(pages)} pages were already saved incrementally.")
            
            # Always update index at the end
            all_saved_pages = [p for p in pages if (p.get("metadata", {}).get("url") or p.get("url", "unknown")) in storage.get_scraped_urls()]
            if all_saved_pages:
                index_entries = []
                for page in all_saved_pages:
                    title = page.get("metadata", {}).get("title", "Untitled")
                    url = page.get("metadata", {}).get("url") or page.get("url", "")
                    page_info = storage.get_page_info(url)
                    if page_info:
                        index_entries.append({
                            "title": title,
                            "url": url,
                            "file": page_info.get("file", "")
                        })
                if index_entries:
                    storage._create_index_file(index_entries)
            
            print(f"✓ Metadata saved to: {config.output_dir}/.scrape_metadata.json")
        else:
            status = result.get("status", "unknown")
            total_pages = result.get("total", 0)
            stats = result.get("stats", {})
            error = result.get("error")
            # Use the job_id from crawl start, fallback to result if needed
            retry_job_id = result.get("id") or result.get("jobId") or job_id
            
            # Check if we saved any pages incrementally even though final result has no data
            saved_urls = storage.get_scraped_urls()
            if saved_urls:
                print(f"\n⚠️  Warning: Crawl finished with status '{status}' but final result has no data.")
                print(f"  However, {len(saved_urls)} page(s) were saved incrementally during the crawl!")
                print(f"  These pages are already saved in: {config.output_dir}")
                # Update index with saved pages
                index_entries = []
                for url in saved_urls:
                    page_info = storage.get_page_info(url)
                    if page_info:
                        # Try to get title from saved file if possible
                        title = url.split('/')[-1] or url  # Fallback title
                        index_entries.append({
                            "title": title,
                            "url": url,
                            "file": page_info.get("file", "")
                        })
                if index_entries:
                    storage._create_index_file(index_entries)
                print(f"\n✓ Found {len(saved_urls)} saved page(s) from incremental saves")
                print(f"✓ Index updated: {config.output_dir}/INDEX.md")
                return  # Exit successfully since we have saved pages
            
            print(f"\n⚠️  Warning: Crawl completed with status '{status}' but no pages found.")
            print(f"  Job ID: {retry_job_id}")
            print(f"  API URL: {config.api_url}")
            print(f"  Response keys: {list(result.keys())}")
            
            if total_pages > 0:
                print(f"  ⚠️  API reports {total_pages} total pages, but data array is empty.")
                print(f"      This indicates a Firecrawl API issue - data not ready or lost.")
            elif total_pages == 0:
                print(f"  ⚠️  API reports 0 total pages - crawl may have found no matching pages.")
            
            if error:
                print(f"  ❌ API Error field: {error}")
            
            if stats:
                print(f"  Stats: {stats}")
            
            # Log full response for debugging (especially useful for VM troubleshooting)
            logger.warning(f"Full API response (no data): {json.dumps(result, indent=2, default=str)}")
            print(f"\n  🔍 Full API response logged to: logs/crawler.log (DEBUG level)")
            
            # Check if we can get the job status again (might have data now)
            if retry_job_id and retry_job_id != "unknown":
                print(f"\n🔄 Attempting to fetch job status again (data might be ready now)...")
                try:
                    retry_result = client.get_crawl_status(retry_job_id)
                    retry_pages = retry_result.get("data", [])
                    if retry_pages:
                        print(f"  ✓ Found {len(retry_pages)} pages on retry!")
                        print("Saving pages...\n")
                        saved_files = storage.save_multiple_pages(retry_pages, create_index=True)
                        print(f"\n✓ Successfully saved {len(saved_files)} pages to: {config.output_dir}")
                        print(f"✓ Metadata saved to: {config.output_dir}/.scrape_metadata.json")
                    else:
                        print(f"  ⚠️  Still no pages in data array")
                        print("\nThis might happen if:")
                        print("  - The crawl is still processing (check again later)")
                        print("  - No pages matched the crawl criteria (depth/limit)")
                        print("  - The website structure changed")
                        print("  - Network/API connectivity issues from VM")
                        print(f"\n💡 Suggestions for VM troubleshooting:")
                        print(f"  - Check logs: tail -f logs/crawler.log")
                        print(f"  - Verify Firecrawl API is accessible: curl {config.api_url}/health")
                        print(f"  - Check if API URL is correct (should be accessible from VM)")
                        print(f"  - Try testing with single page: python3 main.py scrape {section['url']}")
                        print(f"  - Check network connectivity: ping/curl to {config.api_url}")
                        print(f"  - Manually check job status: curl {config.api_url}/v1/crawl/{retry_job_id}")
                        print(f"  - Try running again: python3 crawl_sections.py crawl {section_key}")
                        print(f"  - Use diagnostic tool: python3 diagnose_crawl.py section {section_key}")
                        print(f"  - Retry fetch data: python3 diagnose_crawl.py retry {retry_job_id} --output {config.output_dir}")
                        logger.warning(f"Crawl completed but no pages found for {section['url']}")
                        logger.debug(f"Full result: {result}")
                        logger.debug(f"Retry result: {retry_result}")
                except Exception as e:
                    print(f"  ✗ Error checking job status: {e}")
                    print(f"\n💡 You can manually check the job status later:")
                    print(f"  Job ID: {retry_job_id}")
                    print(f"  API URL: {config.api_url}/v1/crawl/{retry_job_id}")
            else:
                print(f"\n⚠️  Cannot retry: Job ID not available")
                print(f"  Original job_id variable: {job_id if 'job_id' in locals() else 'not found'}")
                print(f"  Result keys: {list(result.keys())}")
                logger.warning(f"Crawl completed but no pages found and job ID unavailable for {section['url']}")
                logger.debug(f"Full result: {result}")
            # Don't exit with error - allow it to continue (might be temporary)
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        sys.exit(1)


def update_section(section_key, sections_config, api_url=None, api_key=None, auto_update=False, show_urls=False):
    """Check for updates in a specific section."""
    if section_key not in sections_config["sections"]:
        print(f"Error: Section '{section_key}' not found")
        sys.exit(1)
    
    section = sections_config["sections"][section_key]
    
    print(f"\n{'='*80}")
    print(f"Checking Updates: {section['name']}")
    print(f"{'='*80}")
    print(f"URL: {section['url']}")
    print(f"Output: {section['output_dir']}\n")
    
    # Use the main.py update functionality
    from main import check_updates
    
    class Args:
        def __init__(self):
            self.url = section['url']
            self.output = section['output_dir']
            self.api_url = api_url
            self.api_key = api_key
            self.show_urls = show_urls
            self.auto_update = auto_update
            self.full_content = False
    
    args = Args()
    check_updates(args)


def crawl_all_sections(sections_config, api_url=None, api_key=None):
    """Crawl all sections sequentially."""
    total_sections = len(sections_config["sections"])
    
    print(f"\n{'='*80}")
    print(f"Crawling ALL {total_sections} Sections")
    print(f"{'='*80}\n")
    
    for i, (key, section) in enumerate(sections_config["sections"].items(), 1):
        print(f"\n[{i}/{total_sections}] Starting section: {section['name']}")
        crawl_section(key, sections_config, api_url, api_key)
        print(f"\n[{i}/{total_sections}] Completed: {section['name']}")


def main():
    parser = argparse.ArgumentParser(
        description="Crawl website sections independently",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available sections
  python crawl_sections.py list
  
  # Crawl a specific section
  python crawl_sections.py crawl admissions
  python crawl_sections.py crawl graduate_school
  
  # Check for updates in a section
  python crawl_sections.py update admissions --show-urls
  python crawl_sections.py update admissions --auto-update
  
  # Crawl all sections
  python crawl_sections.py crawl-all
  
  # Use with custom config file
  python crawl_sections.py crawl admissions --config my_sections.json
        """
    )
    
    parser.add_argument(
        "--config",
        default="sections_config.json",
        help="Path to sections config file (default: sections_config.json)"
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="Firecrawl API URL"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Firecrawl API key"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    subparsers.required = True
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all available sections")
    
    # Crawl command
    crawl_parser = subparsers.add_parser("crawl", help="Crawl a specific section")
    crawl_parser.add_argument("section", help="Section key to crawl")
    crawl_parser.add_argument("--force", action="store_true", help="Force re-crawl even if recent")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Check for updates in a section")
    update_parser.add_argument("section", help="Section key to check")
    update_parser.add_argument("--show-urls", action="store_true", help="Show updated URLs")
    update_parser.add_argument("--auto-update", action="store_true", help="Automatically update changed pages")
    
    # Crawl all command
    crawl_all_parser = subparsers.add_parser("crawl-all", help="Crawl all sections")
    
    args = parser.parse_args()
    
    # Load config
    sections_config = load_sections_config(args.config)
    
    # Execute command
    if args.command == "list":
        list_sections(sections_config)
    elif args.command == "crawl":
        crawl_section(args.section, sections_config, args.api_url, args.api_key, args.force)
    elif args.command == "update":
        update_section(args.section, sections_config, args.api_url, args.api_key, args.auto_update, args.show_urls)
    elif args.command == "crawl-all":
        crawl_all_sections(sections_config, args.api_url, args.api_key)


if __name__ == "__main__":
    main()


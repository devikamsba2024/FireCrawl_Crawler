"""Main CLI interface for Firecrawl crawler."""
import argparse
import sys
from urllib.parse import urlparse
from firecrawl_crawler import (
    Config,
    FirecrawlClient,
    MarkdownStorage,
    SitemapParser,
    setup_logger,
    FirecrawlConnectionError,
    FirecrawlTimeoutError,
    FirecrawlAPIError,
    StorageError
)

# Initialize logger
logger = setup_logger()


def scrape_single_url(args):
    """Scrape a single URL."""
    logger.info(f"=== Starting scrape command for {args.url} ===")
    
    config = Config(
        api_url=args.api_url,
        api_key=args.api_key,
        output_dir=args.output
    )
    
    client = FirecrawlClient(config)
    storage = MarkdownStorage(config.output_dir)
    
    print(f"Scraping: {args.url}")
    logger.debug(f"Full content: {args.full_content}, Wait for: {args.wait_for}")
    
    try:
        # Scrape the URL
        data = client.scrape_url(
            url=args.url,
            formats=["markdown"],
            only_main_content=not args.full_content,
            wait_for=args.wait_for
        )
        
        # Save to markdown
        if data.get("success"):
            filepath = storage.save_single_page(data.get("data", data))
            print(f"\n✓ Successfully saved to: {filepath}")
        else:
            print(f"\n✗ Scraping failed: {data.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except FirecrawlConnectionError as e:
        print(f"\n✗ Connection Error: {str(e)}")
        print("💡 Tip: Make sure Firecrawl is running at http://localhost:3002")
        sys.exit(1)
    except FirecrawlTimeoutError as e:
        print(f"\n✗ Timeout Error: {str(e)}")
        print("💡 Tip: Try increasing --wait-for value")
        sys.exit(1)
    except FirecrawlAPIError as e:
        print(f"\n✗ API Error: {str(e)}")
        sys.exit(1)
    except StorageError as e:
        print(f"\n✗ Storage Error: {str(e)}")
        print("💡 Tip: Check file permissions and disk space")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected Error: {str(e)}")
        print("💡 Tip: Run with python3 -v for more details")
        sys.exit(1)


def crawl_website(args):
    """Crawl an entire website."""
    logger.info(f"=== Starting crawl command for {args.url} ===")
    logger.info(f"Parameters: depth={args.max_depth}, limit={args.limit}, timeout={args.timeout}")
    
    config = Config(
        api_url=args.api_url,
        api_key=args.api_key,
        output_dir=args.output
    )
    
    client = FirecrawlClient(config)
    storage = MarkdownStorage(config.output_dir)
    
    print(f"Starting crawl of: {args.url}")
    print(f"Max depth: {args.max_depth}, Limit: {args.limit}")
    
    try:
        # Start the crawl
        job_id = client.crawl_website(
            url=args.url,
            max_depth=args.max_depth,
            limit=args.limit,
            formats=["markdown"],
            only_main_content=not args.full_content
        )
        
        print(f"Crawl job started: {job_id}")
        print("Waiting for crawl to complete...\n")
        
        # Wait for completion
        result = client.wait_for_crawl(
            job_id=job_id,
            max_wait_time=args.timeout,
            poll_interval=5
        )
        
        # Save all pages
        pages = result.get("data", [])
        if pages:
            print(f"\nCrawl completed! Found {len(pages)} pages.")
            print("Saving pages...\n")
            saved_files = storage.save_multiple_pages(pages, create_index=True)
            print(f"\n✓ Successfully saved {len(saved_files)} pages to: {config.output_dir}")
        else:
            print("\n✗ No pages were scraped")
            sys.exit(1)
            
    except FirecrawlConnectionError as e:
        print(f"\n✗ Connection Error: {str(e)}")
        print("💡 Tip: Make sure Firecrawl is running at http://localhost:3002")
        sys.exit(1)
    except FirecrawlTimeoutError as e:
        print(f"\n✗ Timeout Error: {str(e)}")
        print("💡 Tip: Try increasing --timeout or reducing --limit")
        sys.exit(1)
    except FirecrawlAPIError as e:
        print(f"\n✗ API Error: {str(e)}")
        sys.exit(1)
    except StorageError as e:
        print(f"\n✗ Storage Error: {str(e)}")
        print("💡 Tip: Check file permissions and disk space")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected Error: {str(e)}")
        print("💡 Tip: Run with python3 -v for more details")
        sys.exit(1)


def check_updates(args):
    """Check for updated pages using sitemap."""
    logger.info(f"=== Starting update check for {args.url} ===")
    
    config = Config(
        api_url=args.api_url,
        api_key=args.api_key,
        output_dir=args.output
    )
    
    storage = MarkdownStorage(config.output_dir)
    
    # Parse base URL from args
    base_url = args.url
    parsed = urlparse(base_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    print(f"Checking for updates on: {base_url}")
    print(f"Output directory: {config.output_dir}\n")
    
    try:
        # Parse sitemap
        sitemap = SitemapParser(base_url)
        print("Fetching sitemap...")
        
        # Get previously scraped URLs
        scraped_urls = storage.metadata.get("pages", {})
        print(f"Previously scraped: {len(scraped_urls)} pages")
        
        # Find updated URLs
        path_filter = parsed.path if parsed.path and parsed.path != '/' else None
        updated_urls = sitemap.get_updated_urls(scraped_urls, path_filter)
        
        print(f"Found {len(updated_urls)} pages that need updating\n")
        
        if not updated_urls:
            print("✓ All pages are up to date!")
            return
        
        # Show sample of updates
        if args.show_urls:
            print("Updated URLs:")
            for url in updated_urls[:50]:  # Show first 50
                print(f"  - {url}")
            if len(updated_urls) > 50:
                print(f"  ... and {len(updated_urls) - 50} more")
            print()
        
        # Ask if user wants to update
        if args.auto_update:
            update_pages(updated_urls, config, args)
        else:
            print(f"Run with --auto-update to scrape these {len(updated_urls)} updated pages")
            
    except FirecrawlConnectionError as e:
        print(f"\n✗ Connection Error: {str(e)}")
        print("💡 Tip: Make sure Firecrawl is running")
        sys.exit(1)
    except FirecrawlAPIError as e:
        print(f"\n✗ API Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected Error: {str(e)}")
        sys.exit(1)


def update_pages(urls, config, args):
    """Update a list of specific URLs."""
    client = FirecrawlClient(config)
    storage = MarkdownStorage(config.output_dir)
    
    print(f"Updating {len(urls)} pages...")
    print("This may take a while...\n")
    
    updated_count = 0
    failed_count = 0
    
    for i, url in enumerate(urls, 1):
        try:
            print(f"[{i}/{len(urls)}] Scraping: {url}")
            
            data = client.scrape_url(
                url=url,
                formats=["markdown"],
                only_main_content=not args.full_content
            )
            
            if data.get("success"):
                storage.save_single_page(data.get("data", data))
                updated_count += 1
            else:
                print(f"  ✗ Failed: {data.get('error', 'Unknown error')}")
                failed_count += 1
                
        except (FirecrawlConnectionError, FirecrawlTimeoutError, FirecrawlAPIError) as e:
            print(f"  ✗ Error: {str(e)}")
            failed_count += 1
        except Exception as e:
            print(f"  ✗ Unexpected error: {str(e)}")
            failed_count += 1
    
    print(f"\n✓ Update complete!")
    print(f"  Updated: {updated_count}")
    print(f"  Failed: {failed_count}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Firecrawl crawler - Scrape websites and save as markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape a single page
  python main.py scrape https://example.com
  
  # Crawl an entire website
  python main.py crawl https://example.com --max-depth 3 --limit 50
  
  # Scrape with custom output directory
  python main.py scrape https://example.com -o ./my-docs
  
  # Crawl with custom Firecrawl instance
  python main.py crawl https://example.com --api-url http://localhost:3002
        """
    )
    
    # Global arguments
    parser.add_argument(
        "--api-url",
        default=None,
        help="Firecrawl API URL (default: http://localhost:3002)"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Firecrawl API key (if required)"
    )
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="Output directory for markdown files (default: ./output)"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    subparsers.required = True
    
    # Scrape command
    scrape_parser = subparsers.add_parser(
        "scrape",
        help="Scrape a single URL"
    )
    scrape_parser.add_argument(
        "url",
        help="URL to scrape"
    )
    scrape_parser.add_argument(
        "--full-content",
        action="store_true",
        help="Include all content (default: only main content)"
    )
    scrape_parser.add_argument(
        "--wait-for",
        type=int,
        default=None,
        help="Time to wait for page load in milliseconds"
    )
    scrape_parser.set_defaults(func=scrape_single_url)
    
    # Crawl command
    crawl_parser = subparsers.add_parser(
        "crawl",
        help="Crawl an entire website"
    )
    crawl_parser.add_argument(
        "url",
        help="Starting URL to crawl"
    )
    crawl_parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Maximum crawl depth (default: 2)"
    )
    crawl_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of pages to crawl (default: 10)"
    )
    crawl_parser.add_argument(
        "--full-content",
        action="store_true",
        help="Include all content (default: only main content)"
    )
    crawl_parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Maximum time to wait for crawl completion in seconds (default: 300)"
    )
    crawl_parser.set_defaults(func=crawl_website)
    
    # Update command
    update_parser = subparsers.add_parser(
        "update",
        help="Check for and update changed pages"
    )
    update_parser.add_argument(
        "url",
        help="Base URL or specific path to check for updates"
    )
    update_parser.add_argument(
        "--show-urls",
        action="store_true",
        help="Show list of URLs that need updating"
    )
    update_parser.add_argument(
        "--auto-update",
        action="store_true",
        help="Automatically scrape updated pages"
    )
    update_parser.add_argument(
        "--full-content",
        action="store_true",
        help="Include all content (default: only main content)"
    )
    update_parser.set_defaults(func=check_updates)
    
    # Parse and execute
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


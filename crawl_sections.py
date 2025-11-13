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
        print(f"\n{section['name']} ({key})")
        print(f"  URL: {section['url']}")
        print(f"  Output: {section['output_dir']}")
        print(f"  Limits: max_depth={section['max_depth']}, limit={section['limit']}")
        print(f"  Schedule: {section['schedule']}")
        print(f"  Description: {section['description']}")


def crawl_section(section_key, sections_config, api_url=None, api_key=None, force=False):
    """Crawl a specific section."""
    if section_key not in sections_config["sections"]:
        print(f"Error: Section '{section_key}' not found")
        print(f"Available sections: {', '.join(sections_config['sections'].keys())}")
        sys.exit(1)
    
    section = sections_config["sections"][section_key]
    
    print(f"\n{'='*80}")
    print(f"Crawling: {section['name']}")
    print(f"{'='*80}")
    print(f"URL: {section['url']}")
    print(f"Output: {section['output_dir']}")
    print(f"Max Depth: {section['max_depth']}, Limit: {section['limit']}")
    print()
    
    # Setup config
    config = Config(
        api_url=api_url,
        api_key=api_key,
        output_dir=section['output_dir']
    )
    
    client = FirecrawlClient(config)
    storage = MarkdownStorage(config.output_dir)
    
    try:
        # Start crawl
        job_id = client.crawl_website(
            url=section['url'],
            max_depth=section['max_depth'],
            limit=section['limit'],
            formats=["markdown"],
            only_main_content=True
        )
        
        print(f"Crawl job started: {job_id}")
        print("Waiting for crawl to complete...\n")
        
        # Wait for completion
        result = client.wait_for_crawl(
            job_id=job_id,
            max_wait_time=600,  # 10 minutes
            poll_interval=5
        )
        
        # Save pages
        pages = result.get("data", [])
        if pages:
            print(f"\nCrawl completed! Found {len(pages)} pages.")
            print("Saving pages...\n")
            saved_files = storage.save_multiple_pages(pages, create_index=True)
            print(f"\n✓ Successfully saved {len(saved_files)} pages to: {config.output_dir}")
            print(f"✓ Metadata saved to: {config.output_dir}/.scrape_metadata.json")
        else:
            print("\n✗ No pages were scraped")
            sys.exit(1)
            
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


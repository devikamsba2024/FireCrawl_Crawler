"""Utility functions for change detection and analysis."""
from pathlib import Path
from typing import Dict, List, Any
import json


def get_scrape_stats(output_dir: str) -> Dict[str, Any]:
    """
    Get statistics about scraped content.
    
    Args:
        output_dir: Output directory path
        
    Returns:
        Dictionary with statistics
    """
    output_path = Path(output_dir)
    metadata_file = output_path / ".scrape_metadata.json"
    
    if not metadata_file.exists():
        return {
            "total_pages": 0,
            "last_crawl": None,
            "total_size_mb": 0
        }
    
    metadata = json.loads(metadata_file.read_text())
    pages = metadata.get("pages", {})
    
    # Calculate total size
    total_size = 0
    for page_info in pages.values():
        total_size += page_info.get("file_size", 0)
    
    return {
        "total_pages": len(pages),
        "last_crawl": metadata.get("last_crawl"),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "pages": pages
    }


def list_scraped_pages(output_dir: str, show_details: bool = False) -> None:
    """
    List all scraped pages.
    
    Args:
        output_dir: Output directory path
        show_details: Show detailed information
    """
    stats = get_scrape_stats(output_dir)
    
    print(f"Scraped Pages Statistics")
    print("=" * 50)
    print(f"Total pages: {stats['total_pages']}")
    print(f"Total size: {stats['total_size_mb']} MB")
    print(f"Last crawl: {stats['last_crawl']}")
    print()
    
    if show_details and stats['pages']:
        print("Pages:")
        for url, info in list(stats['pages'].items())[:20]:
            print(f"  • {url}")
            print(f"    File: {info['file']}")
            print(f"    Scraped: {info['scraped_at']}")
            print()
        
        if len(stats['pages']) > 20:
            print(f"  ... and {len(stats['pages']) - 20} more pages")


def compare_scrape_sessions(
    output_dir1: str,
    output_dir2: str
) -> Dict[str, List[str]]:
    """
    Compare two scrape sessions to find differences.
    
    Args:
        output_dir1: First output directory
        output_dir2: Second output directory
        
    Returns:
        Dictionary with added, removed, and common URLs
    """
    stats1 = get_scrape_stats(output_dir1)
    stats2 = get_scrape_stats(output_dir2)
    
    urls1 = set(stats1['pages'].keys())
    urls2 = set(stats2['pages'].keys())
    
    return {
        "only_in_first": sorted(urls1 - urls2),
        "only_in_second": sorted(urls2 - urls1),
        "in_both": sorted(urls1 & urls2)
    }


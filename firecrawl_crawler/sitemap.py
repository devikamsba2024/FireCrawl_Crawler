"""Sitemap parsing utilities for change detection."""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from .logger import get_logger

logger = get_logger(__name__)


class SitemapParser:
    """Parse and analyze XML sitemaps."""
    
    def __init__(self, base_url: str):
        """
        Initialize sitemap parser.
        
        Args:
            base_url: Base URL of the website
        """
        self.base_url = base_url.rstrip('/')
        self.sitemap_url = f"{self.base_url}/sitemap.xml"
    
    def fetch_sitemap(self) -> Optional[str]:
        """
        Fetch sitemap XML content.
        
        Returns:
            Sitemap XML content or None
        """
        try:
            response = requests.get(self.sitemap_url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching sitemap: {e}")
            return None
    
    def parse_sitemap(self, xml_content: str) -> List[Dict[str, str]]:
        """
        Parse sitemap XML into structured data.
        
        Args:
            xml_content: XML content string
            
        Returns:
            List of URL entries with metadata
        """
        urls = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Handle XML namespaces
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            for url_elem in root.findall('sm:url', ns):
                loc = url_elem.find('sm:loc', ns)
                lastmod = url_elem.find('sm:lastmod', ns)
                changefreq = url_elem.find('sm:changefreq', ns)
                priority = url_elem.find('sm:priority', ns)
                
                if loc is not None:
                    entry = {
                        'url': loc.text,
                        'lastmod': lastmod.text if lastmod is not None else None,
                        'changefreq': changefreq.text if changefreq is not None else None,
                        'priority': priority.text if priority is not None else None
                    }
                    urls.append(entry)
        except Exception as e:
            print(f"Error parsing sitemap: {e}")
        
        return urls
    
    def get_all_urls(self) -> List[Dict[str, str]]:
        """
        Get all URLs from sitemap.
        
        Returns:
            List of URL entries
        """
        xml_content = self.fetch_sitemap()
        if xml_content:
            return self.parse_sitemap(xml_content)
        return []
    
    def filter_urls(
        self,
        urls: List[Dict[str, str]],
        path_filter: Optional[str] = None,
        modified_after: Optional[datetime] = None
    ) -> List[Dict[str, str]]:
        """
        Filter URLs based on criteria.
        
        Args:
            urls: List of URL entries
            path_filter: Only include URLs containing this path
            modified_after: Only include URLs modified after this date
            
        Returns:
            Filtered list of URLs
        """
        filtered = urls
        
        # Filter by path
        if path_filter:
            filtered = [u for u in filtered if path_filter in u['url']]
        
        # Filter by modification date
        if modified_after:
            result = []
            for u in filtered:
                if u['lastmod']:
                    try:
                        lastmod = datetime.fromisoformat(u['lastmod'].replace('Z', '+00:00'))
                        if lastmod > modified_after:
                            result.append(u)
                    except Exception:
                        # Include if we can't parse date
                        result.append(u)
                else:
                    # Include if no lastmod
                    result.append(u)
            filtered = result
        
        return filtered
    
    def get_updated_urls(
        self,
        scraped_urls: Dict[str, Dict[str, str]],
        path_filter: Optional[str] = None
    ) -> List[str]:
        """
        Get URLs that have been updated since last scrape.
        
        Args:
            scraped_urls: Dict mapping URL to scrape metadata
            path_filter: Optional path filter
            
        Returns:
            List of URLs that need updating
        """
        sitemap_urls = self.get_all_urls()
        updated = []
        
        for entry in sitemap_urls:
            url = entry['url']
            
            # Apply path filter
            if path_filter and path_filter not in url:
                continue
            
            # Check if URL was previously scraped
            if url in scraped_urls:
                scraped_info = scraped_urls[url]
                scraped_at = scraped_info.get('scraped_at')
                lastmod = entry.get('lastmod')
                
                if scraped_at and lastmod:
                    try:
                        scraped_time = datetime.fromisoformat(scraped_at)
                        modified_time = datetime.fromisoformat(lastmod.replace('Z', '+00:00'))
                        
                        if modified_time > scraped_time:
                            updated.append(url)
                    except Exception:
                        # If we can't parse, assume it needs updating
                        updated.append(url)
            else:
                # New URL not previously scraped
                updated.append(url)
        
        return updated
    
    def analyze_section(
        self,
        section_url: str
    ) -> Dict[str, int]:
        """
        Analyze sitemap to determine page count and depth for a section.
        
        Args:
            section_url: Base URL of the section to analyze
            
        Returns:
            Dict with 'page_count' and 'max_depth' keys
        """
        all_urls = self.get_all_urls()
        if not all_urls:
            logger.warning(f"No URLs found in sitemap for {section_url}")
            return {"page_count": 0, "max_depth": 0}
        
        # Parse section URL to get path
        section_parsed = urlparse(section_url)
        section_path = section_parsed.path.rstrip('/')
        
        # Filter URLs that match this section
        matching_urls = []
        for entry in all_urls:
            url = entry['url']
            url_parsed = urlparse(url)
            url_path = url_parsed.path.rstrip('/')
            
            # Check if URL is under this section
            if url_path.startswith(section_path) or section_path == '':
                matching_urls.append(url_path)
        
        # Calculate depth
        # Depth is relative to section path
        section_depth = len([p for p in section_path.split('/') if p]) if section_path else 0
        max_depth = 0
        
        for url_path in matching_urls:
            # Count path segments after section path
            if section_path:
                relative_path = url_path[len(section_path):].lstrip('/')
            else:
                relative_path = url_path.lstrip('/')
            
            if relative_path:
                depth = len([p for p in relative_path.split('/') if p])
            else:
                depth = 0  # This is the section root itself
            
            max_depth = max(max_depth, depth)
        
        page_count = len(matching_urls)
        
        logger.info(f"Section analysis for {section_url}: {page_count} pages, max_depth={max_depth}")
        
        return {
            "page_count": page_count,
            "max_depth": max_depth
        }


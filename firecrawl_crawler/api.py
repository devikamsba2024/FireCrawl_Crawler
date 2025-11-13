"""Firecrawl API client."""
import requests
import time
from typing import Optional, Dict, Any, List
from .config import Config


class FirecrawlClient:
    """Client for interacting with Firecrawl API."""
    
    def __init__(self, config: Config):
        """
        Initialize Firecrawl client.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.get_headers())
    
    def scrape_url(
        self,
        url: str,
        formats: Optional[List[str]] = None,
        only_main_content: bool = True,
        wait_for: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scrape a single URL.
        
        Args:
            url: URL to scrape
            formats: List of output formats (e.g., ['markdown', 'html'])
            only_main_content: Extract only main content
            wait_for: Time to wait for page load (ms)
            
        Returns:
            Scraped data from Firecrawl
        """
        endpoint = f"{self.config.api_url}/v1/scrape"
        
        payload = {
            "url": url,
            "formats": formats or ["markdown"],
            "onlyMainContent": only_main_content
        }
        
        if wait_for:
            payload["waitFor"] = wait_for
        
        try:
            response = self.session.post(endpoint, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error scraping {url}: {str(e)}")
    
    def crawl_website(
        self,
        url: str,
        max_depth: int = 2,
        limit: int = 10,
        formats: Optional[List[str]] = None,
        only_main_content: bool = True
    ) -> str:
        """
        Crawl a website (multiple pages).
        
        Args:
            url: Starting URL to crawl
            max_depth: Maximum crawl depth
            limit: Maximum number of pages to crawl
            formats: List of output formats
            only_main_content: Extract only main content
            
        Returns:
            Job ID for the crawl operation
        """
        endpoint = f"{self.config.api_url}/v1/crawl"
        
        payload = {
            "url": url,
            "limit": limit,
            "scrapeOptions": {
                "formats": formats or ["markdown"],
                "onlyMainContent": only_main_content
            },
            "maxDepth": max_depth
        }
        
        try:
            response = self.session.post(endpoint, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data.get("id") or data.get("jobId")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error starting crawl for {url}: {str(e)}")
    
    def get_crawl_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a crawl job.
        
        Args:
            job_id: Job ID from crawl_website
            
        Returns:
            Job status and data
        """
        endpoint = f"{self.config.api_url}/v1/crawl/{job_id}"
        
        try:
            response = self.session.get(endpoint, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error getting crawl status: {str(e)}")
    
    def wait_for_crawl(
        self,
        job_id: str,
        max_wait_time: int = 300,
        poll_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Wait for a crawl job to complete.
        
        Args:
            job_id: Job ID from crawl_website
            max_wait_time: Maximum time to wait (seconds)
            poll_interval: Time between status checks (seconds)
            
        Returns:
            Final job data with all scraped pages
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_data = self.get_crawl_status(job_id)
            status = status_data.get("status")
            
            if status == "completed":
                return status_data
            elif status == "failed":
                raise Exception(f"Crawl job {job_id} failed")
            
            print(f"Crawl status: {status}, waiting...")
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Crawl job {job_id} timed out after {max_wait_time}s")


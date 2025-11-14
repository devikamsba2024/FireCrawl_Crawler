"""Firecrawl API client."""
import requests
import time
from typing import Optional, Dict, Any, List
from .config import Config
from .logger import get_logger
from .exceptions import FirecrawlAPIError, FirecrawlConnectionError, FirecrawlTimeoutError

logger = get_logger(__name__)


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
        logger.debug(f"Initialized FirecrawlClient with URL: {config.api_url}")
    
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
        
        logger.debug(f"Scraping URL: {url}")
        logger.debug(f"Payload: {payload}")
        
        try:
            response = self.session.post(endpoint, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully scraped: {url}")
            return data
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error scraping {url}: {e}")
            raise FirecrawlConnectionError(
                f"Cannot connect to Firecrawl at {self.config.api_url}. "
                f"Is it running? Error: {str(e)}"
            )
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout scraping {url}: {e}")
            raise FirecrawlTimeoutError(f"Timeout scraping {url}: {str(e)}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error scraping {url}: {e.response.status_code} - {e}")
            raise FirecrawlAPIError(
                f"HTTP error scraping {url}: {e.response.status_code} - {str(e)}"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error scraping {url}: {e}")
            raise FirecrawlAPIError(f"Error scraping {url}: {str(e)}")
    
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
        
        logger.info(f"Starting crawl: {url} (depth={max_depth}, limit={limit})")
        logger.debug(f"Crawl payload: {payload}")
        
        try:
            response = self.session.post(endpoint, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            job_id = data.get("id") or data.get("jobId")
            if not job_id:
                logger.error(f"No job ID in response for {url}")
                raise FirecrawlAPIError(f"No job ID returned from crawl API for {url}")
            logger.info(f"Crawl job started: {job_id}")
            return job_id
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error starting crawl for {url}: {e}")
            raise FirecrawlConnectionError(
                f"Cannot connect to Firecrawl at {self.config.api_url}. "
                f"Is it running? Error: {str(e)}"
            )
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout starting crawl for {url}: {e}")
            raise FirecrawlTimeoutError(f"Timeout starting crawl for {url}: {str(e)}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error starting crawl for {url}: {e.response.status_code} - {e}")
            raise FirecrawlAPIError(
                f"HTTP error starting crawl for {url}: {e.response.status_code} - {str(e)}"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error starting crawl for {url}: {e}")
            raise FirecrawlAPIError(f"Error starting crawl for {url}: {str(e)}")
    
    def get_crawl_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a crawl job.
        
        Args:
            job_id: Job ID from crawl_website
            
        Returns:
            Job status and data
        """
        endpoint = f"{self.config.api_url}/v1/crawl/{job_id}"
        
        logger.debug(f"Checking crawl status for job: {job_id}")
        
        try:
            response = self.session.get(endpoint, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error getting status for {job_id}: {e}")
            raise FirecrawlConnectionError(
                f"Cannot connect to Firecrawl at {self.config.api_url}: {str(e)}"
            )
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout getting status for {job_id}: {e}")
            raise FirecrawlTimeoutError(f"Timeout getting crawl status for job {job_id}: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting status for {job_id}: {e}")
            raise FirecrawlAPIError(f"Error getting crawl status for job {job_id}: {str(e)}")
    
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
        logger.info(f"Waiting for crawl job {job_id} to complete (max {max_wait_time}s)")
        
        while time.time() - start_time < max_wait_time:
            status_data = self.get_crawl_status(job_id)
            status = status_data.get("status")
            
            if status == "completed":
                # Check if data is available (sometimes completed but data not ready yet)
                pages = status_data.get("data", [])
                if pages:
                    logger.info(f"Crawl job {job_id} completed successfully with {len(pages)} pages")
                    return status_data
                else:
                    # Status is completed but no data yet - wait a bit more
                    logger.debug(f"Crawl job {job_id} marked completed but no data yet, waiting...")
                    print(f"Crawl status: {status} (waiting for data...), waiting...")
                    time.sleep(poll_interval)
                    # Give it a few more tries (up to 30 seconds)
                    retry_count = 0
                    max_retries = 6  # 6 * 5s = 30 seconds
                    while retry_count < max_retries and time.time() - start_time < max_wait_time:
                        status_data = self.get_crawl_status(job_id)
                        pages = status_data.get("data", [])
                        if pages:
                            logger.info(f"Crawl job {job_id} data now available: {len(pages)} pages")
                            return status_data
                        retry_count += 1
                        time.sleep(poll_interval)
                    
                    # If still no data after retries, return what we have
                    logger.warning(f"Crawl job {job_id} completed but no pages found after retries")
                    logger.debug(f"Status data keys: {list(status_data.keys())}")
                    logger.debug(f"Status data: {status_data}")
                    return status_data
            elif status == "failed":
                error_msg = status_data.get("error", "Unknown error")
                logger.error(f"Crawl job {job_id} failed: {error_msg}")
                raise FirecrawlAPIError(f"Crawl job {job_id} failed: {error_msg}")
            
            logger.debug(f"Crawl status: {status}, waiting...")
            print(f"Crawl status: {status}, waiting...")
            time.sleep(poll_interval)
        
        logger.error(f"Crawl job {job_id} timed out after {max_wait_time}s")
        raise FirecrawlTimeoutError(
            f"Crawl job {job_id} timed out after {max_wait_time}s. "
            f"Last status: {status_data.get('status', 'unknown')}"
        )


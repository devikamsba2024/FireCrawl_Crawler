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
                    # Status is completed but no data yet - keep waiting until data arrives
                    logger.debug(f"Crawl job {job_id} marked completed but no data yet, waiting for data...")
                    print(f"Crawl status: {status} (waiting for data...), waiting...")
                    
                    # Keep polling until data is available or timeout
                    data_wait_start = time.time()
                    max_data_wait = min(60, max_wait_time - (time.time() - start_time))  # Wait up to 60s or remaining time
                    
                    while time.time() - data_wait_start < max_data_wait and time.time() - start_time < max_wait_time:
                        status_data = self.get_crawl_status(job_id)
                        pages = status_data.get("data", [])
                        current_status = status_data.get("status", status)
                        
                        if pages:
                            logger.info(f"Crawl job {job_id} data now available: {len(pages)} pages")
                            return status_data
                        
                        # If status changed from completed, break and continue main loop
                        if current_status != "completed":
                            logger.debug(f"Status changed from completed to {current_status}, continuing...")
                            break
                        
                        logger.debug(f"Still waiting for data... (elapsed: {int(time.time() - data_wait_start)}s)")
                        print(f"Crawl status: {current_status} (waiting for data...), waiting...")
                        time.sleep(poll_interval)
                    
                    # If we exhausted the wait time and still no data, check one more time
                    final_status_data = self.get_crawl_status(job_id)
                    final_pages = final_status_data.get("data", [])
                    if final_pages:
                        logger.info(f"Crawl job {job_id} data available on final check: {len(final_pages)} pages")
                        return final_status_data
                    
                    # If still no data, this might be a real issue - but don't return completed without data
                    # Instead, treat it as if still processing and let timeout handle it
                    if not final_pages:
                        logger.warning(f"Crawl job {job_id} marked completed but no data after extended wait")
                        logger.debug(f"Status data keys: {list(status_data.keys())}")
                        logger.debug(f"Status data: {status_data}")
                        # Continue the loop - don't return completed without data
                        # This will either timeout or eventually get data
                        print(f"Crawl status: {status} (no data yet, continuing to wait...), waiting...")
                        time.sleep(poll_interval)
                        continue
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


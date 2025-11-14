"""Firecrawl API client."""
import json
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
        completed_without_data_count = 0  # Track consecutive "completed" status with no data
        max_completed_without_data = 3  # Max times to see "completed" without data before returning
        
        while time.time() - start_time < max_wait_time:
            status_data = self.get_crawl_status(job_id)
            status = status_data.get("status")
            
            if status == "completed":
                # Check if data is available (sometimes completed but data not ready yet)
                pages = status_data.get("data", [])
                total_pages = status_data.get("total", 0)
                stats = status_data.get("stats", {})
                error = status_data.get("error")
                
                # Log diagnostic info when completed but no data
                if not pages:
                    logger.debug(
                        f"Crawl job {job_id} status: completed, "
                        f"data: {len(pages)} pages, "
                        f"total: {total_pages}, "
                        f"stats: {stats}, "
                        f"error: {error}, "
                        f"keys: {list(status_data.keys())}"
                    )
                
                if pages:
                    logger.info(f"Crawl job {job_id} completed successfully with {len(pages)} pages")
                    return status_data
                else:
                    # Status is completed but no data yet - wait for data, but don't loop forever
                    completed_without_data_count += 1
                    
                    if completed_without_data_count == 1:
                        # First time seeing completed without data - wait for data
                        logger.debug(f"Crawl job {job_id} marked completed but no data yet, waiting for data...")
                        if total_pages > 0:
                            logger.warning(
                                f"API reports {total_pages} total pages but data array is empty - "
                                f"this may be a Firecrawl API timing issue"
                            )
                            print(f"Crawl status: {status} (API reports {total_pages} pages but data not ready), waiting...")
                        elif error:
                            logger.warning(f"API reports completed but has error field: {error}")
                            print(f"Crawl status: {status} (has error: {error}), waiting...")
                        else:
                            print(f"Crawl status: {status} (waiting for data...), waiting...")
                        
                        # Keep polling until data is available or timeout
                        data_wait_start = time.time()
                        remaining_time = max_wait_time - (time.time() - start_time)
                        max_data_wait = min(60, remaining_time)  # Wait up to 60s or remaining time
                        
                        pages_found = False
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
                                completed_without_data_count = 0  # Reset counter
                                break
                            
                            logger.debug(f"Still waiting for data... (elapsed: {int(time.time() - data_wait_start)}s)")
                            print(f"Crawl status: {current_status} (waiting for data...), waiting...")
                            time.sleep(poll_interval)
                            pages_found = bool(pages)
                        
                        # Final check after waiting period
                        if not pages_found:
                            final_status_data = self.get_crawl_status(job_id)
                            final_pages = final_status_data.get("data", [])
                            if final_pages:
                                logger.info(f"Crawl job {job_id} data available on final check: {len(final_pages)} pages")
                                return final_status_data
                            status_data = final_status_data
                    
                    # If we've seen "completed" without data multiple times, return the result anyway
                    # This prevents infinite loops while still allowing caller to handle empty data
                    if completed_without_data_count >= max_completed_without_data:
                        # Get final diagnostic info
                        final_total = status_data.get("total", 0)
                        final_stats = status_data.get("stats", {})
                        final_error = status_data.get("error")
                        
                        # Log full response for debugging
                        logger.warning(
                            f"Crawl job {job_id} marked completed but no data after {completed_without_data_count} checks. "
                            f"Total reported: {final_total}, Stats: {final_stats}, Error: {final_error}. "
                            f"This appears to be a Firecrawl API issue - returning result with empty data array."
                        )
                        logger.debug(f"Full API response: {json.dumps(status_data, indent=2, default=str)}")
                        
                        # Print diagnostic info to console
                        print(f"\n⚠️  API returned 'completed' but no data after {completed_without_data_count} checks")
                        print(f"    This is likely a Firecrawl API issue from your VM.")
                        print(f"    Check logs/crawler.log for full API response details.")
                        
                        # Return the status_data even without pages - caller can handle this
                        return status_data
                    
                    # Log warning but continue waiting (will check again on next iteration)
                    logger.warning(f"Crawl job {job_id} marked completed but no data after extended wait (attempt {completed_without_data_count}/{max_completed_without_data})")
                    print(f"Crawl status: {status} (no data yet, continuing to wait...), waiting...")
                    time.sleep(poll_interval)
                    continue
            elif status == "failed":
                error_msg = status_data.get("error", "Unknown error")
                logger.error(f"Crawl job {job_id} failed: {error_msg}")
                raise FirecrawlAPIError(f"Crawl job {job_id} failed: {error_msg}")
            
            # Reset counter if status is not "completed"
            if status != "completed":
                completed_without_data_count = 0
            
            logger.debug(f"Crawl status: {status}, waiting...")
            print(f"Crawl status: {status}, waiting...")
            time.sleep(poll_interval)
        
        logger.error(f"Crawl job {job_id} timed out after {max_wait_time}s")
        raise FirecrawlTimeoutError(
            f"Crawl job {job_id} timed out after {max_wait_time}s. "
            f"Last status: {status_data.get('status', 'unknown')}"
        )


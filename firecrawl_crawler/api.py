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
    
    def check_connection(self) -> bool:
        """
        Check if Firecrawl API is accessible.
        
        Returns:
            True if API is accessible, False otherwise
        """
        # Try health endpoint first
        try:
            health_url = f"{self.config.api_url}/health"
            response = self.session.get(health_url, timeout=5)
            response.raise_for_status()
            logger.debug(f"Health check successful: {health_url}")
            return True
        except requests.exceptions.HTTPError as e:
            # If health endpoint doesn't exist (404), try alternative check
            if e.response.status_code == 404:
                logger.debug(f"Health endpoint not found (404), trying alternative check")
                # Try a simple API endpoint to verify API is accessible
                return self._check_connection_alternative()
            logger.debug(f"Health check failed - HTTP error: {e.response.status_code}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.debug(f"Health check failed - connection error: {e}")
            return False
        except requests.exceptions.Timeout:
            logger.debug(f"Health check failed - timeout")
            return False
        except Exception as e:
            logger.debug(f"Health check failed - {type(e).__name__}: {e}")
            # Try alternative check as fallback
            return self._check_connection_alternative()
    
    def _check_connection_alternative(self) -> bool:
        """
        Alternative connection check if health endpoint doesn't exist.
        Tries to access the API root or a known endpoint.
        
        Returns:
            True if API appears to be accessible, False otherwise
        """
        try:
            # Try accessing the API root or a simple endpoint
            # Many APIs respond to root with some info
            test_urls = [
                f"{self.config.api_url}/",
                f"{self.config.api_url}/v1",
            ]
            
            for test_url in test_urls:
                try:
                    response = self.session.get(test_url, timeout=5)
                    # If we get any response (not connection error), API is likely accessible
                    logger.debug(f"Alternative check successful: {test_url} (status: {response.status_code})")
                    return True
                except requests.exceptions.HTTPError:
                    # HTTP errors (like 404) mean server is responding - that's good
                    logger.debug(f"Alternative check - server responding at {test_url}")
                    return True
                except requests.exceptions.ConnectionError:
                    continue
                except requests.exceptions.Timeout:
                    continue
            
            # If all endpoints fail, try a HEAD request to see if server responds at all
            try:
                response = self.session.head(f"{self.config.api_url}/", timeout=5)
                logger.debug(f"Alternative check successful via HEAD request")
                return True
            except:
                pass
            
            logger.debug(f"Alternative connection check failed")
            return False
        except Exception as e:
            logger.debug(f"Alternative connection check error: {e}")
            return False
    
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
        
        # Retry on 408 errors with longer timeout
        max_retries = 3
        retry_delays = [2, 5, 10]
        timeouts = [120, 150, 180]  # Increasing timeouts for retries (start with 120s which works)
        
        for attempt in range(max_retries):
            try:
                current_timeout = timeouts[min(attempt, len(timeouts) - 1)]
                logger.debug(f"Scrape attempt {attempt + 1}/{max_retries} with {current_timeout}s timeout")
                print(f"  Attempt {attempt + 1}/{max_retries}: Using {current_timeout}s timeout...")
                response = self.session.post(endpoint, json=payload, timeout=current_timeout)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Successfully scraped: {url} on attempt {attempt + 1}")
                print(f"  ✓ Scrape successful on attempt {attempt + 1}")
                return data
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                logger.warning(f"HTTP error {status_code} on attempt {attempt + 1}/{max_retries}")
                
                # Handle 408 Request Timeout specifically
                if status_code == 408:
                    if attempt < max_retries - 1:
                        next_attempt = attempt + 1
                        next_timeout = timeouts[min(next_attempt, len(timeouts) - 1)]
                        delay = retry_delays[attempt]
                        logger.warning(
                            f"408 Request Timeout scraping {url} (attempt {attempt + 1}/{max_retries}). "
                            f"Server timed out at {current_timeout}s. "
                            f"Retrying attempt {next_attempt + 1} with {next_timeout}s timeout after {delay}s delay..."
                        )
                        print(f"⚠️  408 Request Timeout (attempt {attempt + 1}/{max_retries})")
                        print(f"    Server timed out. Retrying in {delay}s with {next_timeout}s timeout...")
                        time.sleep(delay)
                        continue
                    else:
                        # Final attempt failed - server timeout issue
                        logger.error(f"408 Request Timeout scraping {url} after {max_retries} attempts")
                        print(f"✗ All {max_retries} attempts failed with 408 Request Timeout")
                        print(f"\n⚠️  IMPORTANT: The Firecrawl API server itself is timing out.")
                        print(f"    This is a server-side timeout (not client-side).")
                        print(f"    The server has its own timeout limit (likely 60-90 seconds).")
                        print(f"\n💡 SOLUTIONS:")
                        print(f"    1. Use CRAWL instead of SCRAPE:")
                        print(f"       - Crawl handles slow pages better (async, no timeout)")
                        print(f"       - Example: python crawl_sections.py crawl <section>")
                        print(f"    2. Check Firecrawl server timeout configuration")
                        print(f"    3. Test URL directly: curl {url}")
                        print(f"    4. Try scraping a different, faster page")
                        raise FirecrawlTimeoutError(
                            f"Request timeout (408) scraping {url} after {max_retries} attempts. "
                            f"Tried client timeouts: {', '.join(map(str, timeouts))}s\n"
                            f"\n⚠️  SERVER-SIDE TIMEOUT: The Firecrawl API server is timing out.\n"
                            f"    The server has its own timeout (likely 60-90s) which we cannot control.\n"
                            f"    Increasing client timeout won't help if server always times out.\n"
                            f"\n💡 SOLUTION: Use CRAWL instead of SCRAPE for slow pages.\n"
                            f"    Crawl is async and doesn't have the same timeout limitations.\n"
                            f"    Example: python crawl_sections.py crawl <section>\n"
                            f"\nOther options:\n"
                            f"  - Check Firecrawl server timeout configuration\n"
                            f"  - Test URL directly: curl {url}\n"
                            f"  - Try a different, faster page"
                        )
                else:
                    # Other HTTP errors - don't retry
                    logger.error(f"HTTP error scraping {url}: {e.response.status_code} - {e}")
                    raise FirecrawlAPIError(
                        f"HTTP error scraping {url}: {e.response.status_code} - {str(e)}"
                    )
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(
                        f"Connection error scraping {url} (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay}s..."
                    )
                    print(f"⚠️  Connection error - retrying... ({attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    # Final attempt failed
                    logger.error(f"Connection error scraping {url}: {e}")
                    
                    # Try to check if API is accessible
                    is_accessible = self.check_connection()
                    
                    error_msg = (
                        f"Cannot connect to Firecrawl API at {self.config.api_url}.\n"
                        f"  Attempted endpoint: {endpoint}\n"
                    )
                    
                    if not is_accessible:
                        error_msg += (
                            f"  Health check failed - API is not accessible.\n"
                            f"  This may be due to:\n"
                            f"    - Firecrawl is not running\n"
                            f"    - Network connectivity issues (especially from VM)\n"
                            f"    - Firewall blocking connections\n"
                            f"    - Wrong API URL (check if accessible from this machine)\n"
                            f"  Try: curl {self.config.api_url}/health\n"
                        )
                    else:
                        error_msg += (
                            f"  Health check passed, but scrape endpoint failed.\n"
                            f"  This suggests the API is running but the endpoint may have issues.\n"
                        )
                    
                    error_msg += f"  Original error: {str(e)}"
                    
                    raise FirecrawlConnectionError(error_msg)
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    current_timeout = timeouts[min(attempt + 1, len(timeouts) - 1)]
                    logger.warning(
                        f"Connection timeout scraping {url} (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying with longer timeout ({current_timeout}s) in {delay}s..."
                    )
                    print(f"⚠️  Connection timeout - retrying with longer timeout... ({attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Timeout scraping {url} after {max_retries} attempts: {e}")
                    raise FirecrawlTimeoutError(
                        f"Timeout scraping {url} after {max_retries} attempts. "
                        f"The page may be too slow to load or unreachable."
                    )
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(
                        f"Request error scraping {url} (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Request error scraping {url}: {e}")
                    raise FirecrawlAPIError(f"Error scraping {url}: {str(e)}")
        
        # This should never be reached, but just in case
        raise FirecrawlAPIError(f"Unexpected error scraping {url}")
    
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
            
            # Try to check if API is accessible
            is_accessible = self.check_connection()
            
            error_msg = (
                f"Cannot connect to Firecrawl API at {self.config.api_url}.\n"
                f"  Attempted endpoint: {endpoint}\n"
            )
            
            if not is_accessible:
                error_msg += (
                    f"  Health check failed - API is not accessible.\n"
                    f"  This may be due to:\n"
                    f"    - Firecrawl is not running\n"
                    f"    - Network connectivity issues (especially from VM)\n"
                    f"    - Firewall blocking connections\n"
                    f"    - Wrong API URL (check if accessible from this machine)\n"
                    f"  Try: curl {self.config.api_url}/health\n"
                )
            else:
                error_msg += (
                    f"  Health check passed, but crawl endpoint failed.\n"
                    f"  This suggests the API is running but the endpoint may have issues.\n"
                )
            
            error_msg += f"  Original error: {str(e)}"
            
            raise FirecrawlConnectionError(error_msg)
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
    
    def get_crawl_status(self, job_id: str, retry_on_connection_error: bool = True) -> Dict[str, Any]:
        """
        Get status of a crawl job.
        
        Args:
            job_id: Job ID from crawl_website
            retry_on_connection_error: If True, retry on connection errors (default: True)
            
        Returns:
            Job status and data
        """
        endpoint = f"{self.config.api_url}/v1/crawl/{job_id}"
        
        logger.debug(f"Checking crawl status for job: {job_id}")
        
        max_retries = 3 if retry_on_connection_error else 1
        retry_delays = [2, 5, 10]  # Exponential backoff in seconds
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(endpoint, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    # Retry transient connection errors
                    delay = retry_delays[attempt]
                    logger.warning(
                        f"Connection error getting status for {job_id} (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue
                else:
                    # Final attempt failed
                    logger.error(f"Connection error getting status for {job_id} after {max_retries} attempts: {e}")
                    
                    # Try to check if API is accessible
                    is_accessible = self.check_connection()
                    
                    error_msg = (
                        f"Cannot connect to Firecrawl API at {self.config.api_url} after {max_retries} attempts.\n"
                        f"  Attempted endpoint: {endpoint}\n"
                    )
                    
                    if not is_accessible:
                        error_msg += (
                            f"  Health check failed - API connection lost during crawl.\n"
                            f"  This may indicate:\n"
                            f"    - Firecrawl service stopped/crashed\n"
                            f"    - Network connectivity issues (especially from VM)\n"
                            f"    - Job {job_id} may still be running on server\n"
                        )
                    else:
                        error_msg += (
                            f"  Health check passed, but status endpoint failed.\n"
                            f"  The API is accessible but status check failed.\n"
                        )
                    
                    error_msg += f"  Original error: {str(e)}"
                    
                    raise FirecrawlConnectionError(error_msg)
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout getting status for {job_id}: {e}")
                raise FirecrawlTimeoutError(f"Timeout getting crawl status for job {job_id}: {str(e)}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error getting status for {job_id}: {e}")
                raise FirecrawlAPIError(f"Error getting crawl status for job {job_id}: {str(e)}")
        
        # This should never be reached, but just in case
        raise FirecrawlAPIError(f"Unexpected error getting crawl status for job {job_id}")
    
    def wait_for_crawl(
        self,
        job_id: str,
        max_wait_time: Optional[int] = None,
        poll_interval: int = 5,
        incremental_save: Optional[Any] = None  # MarkdownStorage instance for incremental saving
    ) -> Dict[str, Any]:
        """
        Wait for a crawl job to complete.
        
        Args:
            job_id: Job ID from crawl_website
            max_wait_time: Maximum time to wait (seconds). None means wait indefinitely.
            poll_interval: Time between status checks (seconds)
            incremental_save: Optional MarkdownStorage instance to save pages as they come in.
                            If provided, pages will be saved incrementally during status checks.
            
        Returns:
            Final job data with all scraped pages
        """
        start_time = time.time()
        if max_wait_time is None:
            logger.info(f"Waiting for crawl job {job_id} to complete (no timeout)")
        else:
            logger.info(f"Waiting for crawl job {job_id} to complete (max {max_wait_time}s)")
        completed_without_data_count = 0  # Track consecutive "completed" status with no data
        max_completed_without_data = 3  # Max times to see "completed" without data before returning
        consecutive_connection_errors = 0  # Track consecutive connection errors
        max_consecutive_connection_errors = 5  # Max connection errors before giving up
        saved_page_urls = set()  # Track which pages we've already saved for incremental saving
        scraping_start_time = None  # Track when scraping status started
        last_scraping_status_time = None  # Track last time we saw scraping status
        
        while max_wait_time is None or time.time() - start_time < max_wait_time:
            try:
                status_data = self.get_crawl_status(job_id, retry_on_connection_error=True)
                consecutive_connection_errors = 0  # Reset on successful connection
            except FirecrawlConnectionError as e:
                consecutive_connection_errors += 1
                
                if consecutive_connection_errors >= max_consecutive_connection_errors:
                    logger.error(
                        f"Crawl job {job_id} - {max_consecutive_connection_errors} consecutive connection errors. "
                        f"Giving up. Job may still be running on server."
                    )
                    raise FirecrawlConnectionError(
                        f"Crawl job {job_id} failed due to persistent connection issues.\n"
                        f"  The job may still be running on the server.\n"
                        f"  You can check status later with: {self.config.api_url}/v1/crawl/{job_id}\n"
                        f"  Original error: {str(e)}"
                    )
                
                # Log warning but continue trying
                logger.warning(
                    f"Connection error checking status for {job_id} "
                    f"({consecutive_connection_errors}/{max_consecutive_connection_errors}). "
                    f"Will retry..."
                )
                print(f"Crawl status: connection error, retrying... ({consecutive_connection_errors}/{max_consecutive_connection_errors})")
                time.sleep(poll_interval * 2)  # Wait longer before retrying
                continue
            
            status = status_data.get("status")
            
            # Get diagnostic info for all statuses, not just completed
            pages = status_data.get("data", [])
            total_pages = status_data.get("total", 0)
            stats = status_data.get("stats", {})
            
            # Log diagnostic info during scraping to help debug
            if status == "scraping":
                if scraping_start_time is None:
                    scraping_start_time = time.time()
                    logger.debug(f"Crawl job {job_id} started scraping status")
                
                last_scraping_status_time = time.time()
                scraping_duration = int(time.time() - scraping_start_time)
                elapsed = int(time.time() - start_time)
                
                logger.debug(
                    f"Crawl job {job_id} status: scraping (duration: {scraping_duration}s), "
                    f"data: {len(pages)} pages, "
                    f"total: {total_pages}, "
                    f"stats: {stats}, "
                    f"keys: {list(status_data.keys())}"
                )
                
                # Warn if scraping for a long time with no data
                if scraping_duration > 300 and len(pages) == 0:  # 5 minutes with no data
                    print(f"⚠️  WARNING: Crawl has been 'scraping' for {scraping_duration}s with no data yet.")
                    print(f"    This may indicate the crawl is stuck or server is slow.")
                    print(f"    Job ID: {job_id}")
                    if total_pages > 0:
                        print(f"    API reports {total_pages} total pages, but data array is empty.")
                    print(f"    You can check status manually: curl {self.config.api_url}/v1/crawl/{job_id}")
                
                # Show progress if we have stats or pages
                if stats or len(pages) > 0:
                    print(f"Crawl status: {status} (elapsed: {elapsed}s, pages found: {len(pages)}, total: {total_pages})")
            else:
                # Reset scraping timer if status changed
                if scraping_start_time is not None:
                    scraping_duration = int(time.time() - scraping_start_time) if scraping_start_time else 0
                    logger.debug(f"Crawl job {job_id} exited scraping status after {scraping_duration}s")
                    scraping_start_time = None
            
            # Check for partial data and save incrementally if enabled (works during scraping too)
            if pages and incremental_save:
                new_pages = []
                for p in pages:
                    page_url = p.get("metadata", {}).get("url") or p.get("url", "unknown")
                    if page_url not in saved_page_urls:
                        new_pages.append(p)
                
                if new_pages:
                    try:
                        print(f"  Saving {len(new_pages)} new page(s) incrementally...")
                        for page in new_pages:
                            page_url = page.get("metadata", {}).get("url") or page.get("url", "unknown")
                            if page_url not in saved_page_urls:
                                incremental_save.save_single_page(page)
                                saved_page_urls.add(page_url)
                                logger.info(f"Incrementally saved page: {page_url}")
                    except Exception as e:
                        logger.warning(f"Error during incremental save: {e}")
                        # Continue anyway
            
            if status == "completed":
                # Check if data is available (sometimes completed but data not ready yet)
                # Note: total_pages, stats, error are already extracted above
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
                    # Save any remaining pages that weren't saved incrementally
                    if incremental_save:
                        remaining_pages = []
                        for p in pages:
                            page_url = p.get("metadata", {}).get("url") or p.get("url", "unknown")
                            if page_url not in saved_page_urls:
                                remaining_pages.append(p)
                        
                        if remaining_pages:
                            try:
                                print(f"  Saving {len(remaining_pages)} remaining page(s)...")
                                for page in remaining_pages:
                                    incremental_save.save_single_page(page)
                            except Exception as e:
                                logger.warning(f"Error saving remaining pages: {e}")
                    
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
                        if max_wait_time is None:
                            max_data_wait = 60  # Wait up to 60s for data when no timeout
                        else:
                            remaining_time = max_wait_time - (time.time() - start_time)
                            max_data_wait = min(60, remaining_time)  # Wait up to 60s or remaining time
                        
                        pages_found = False
                        while (max_wait_time is None or time.time() - start_time < max_wait_time) and time.time() - data_wait_start < max_data_wait:
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
            
            # Show progress for scraping status with more info
            if status == "scraping":
                elapsed_time = int(time.time() - start_time)
                if total_pages > 0:
                    print(f"Crawl status: {status} (elapsed: {elapsed_time}s, total pages: {total_pages}, data: {len(pages)} pages)...")
                elif len(pages) > 0:
                    print(f"Crawl status: {status} (elapsed: {elapsed_time}s, found {len(pages)} page(s) so far)...")
                else:
                    print(f"Crawl status: {status} (elapsed: {elapsed_time}s), waiting...")
                logger.debug(f"Crawl status: {status}, elapsed: {elapsed_time}s, pages: {len(pages)}, total: {total_pages}")
            else:
                logger.debug(f"Crawl status: {status}, waiting...")
                print(f"Crawl status: {status}, waiting...")
            
            time.sleep(poll_interval)
        
        # Only timeout if max_wait_time was set
        if max_wait_time is not None:
            logger.error(f"Crawl job {job_id} timed out after {max_wait_time}s")
            raise FirecrawlTimeoutError(
                f"Crawl job {job_id} timed out after {max_wait_time}s. "
                f"Last status: {status_data.get('status', 'unknown')}"
            )
        else:
            # This should never happen (infinite loop broken above), but just in case
            logger.error(f"Crawl job {job_id} exited wait loop unexpectedly")
            raise FirecrawlAPIError(
                f"Crawl job {job_id} wait loop exited unexpectedly. "
                f"Last status: {status_data.get('status', 'unknown')}"
            )


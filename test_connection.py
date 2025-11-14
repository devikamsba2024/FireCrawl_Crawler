#!/usr/bin/env python3
"""
Test script to check Firecrawl API connectivity and website accessibility.
Useful for troubleshooting VM connectivity issues.
"""
import argparse
import sys
import time
from pathlib import Path
from firecrawl_crawler import Config, FirecrawlClient
from firecrawl_crawler.exceptions import FirecrawlConnectionError, FirecrawlAPIError, FirecrawlTimeoutError


def test_api_connection(api_url: str, api_key: str = None):
    """Test basic API connection."""
    print("\n" + "="*80)
    print("TEST 1: API Connection Check")
    print("="*80)
    
    try:
        config = Config(api_url=api_url, api_key=api_key)
        client = FirecrawlClient(config)
        
        print(f"API URL: {api_url}")
        print(f"Testing connection...")
        
        if client.check_connection():
            print("✓ API connection successful!")
            return True
        else:
            print("✗ API connection failed - health check returned False")
            return False
            
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False


def test_health_endpoint(api_url: str):
    """Test health endpoint directly."""
    print("\n" + "="*80)
    print("TEST 2: Health Endpoint Check")
    print("="*80)
    
    import requests
    
    health_url = f"{api_url}/health"
    print(f"Health endpoint: {health_url}")
    print("Testing...")
    
    try:
        response = requests.get(health_url, timeout=5)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print("✓ Health endpoint is accessible")
            return True
        else:
            print(f"✗ Health endpoint returned non-200 status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error: {e}")
        print("\n💡 Troubleshooting:")
        print(f"  - Is Firecrawl running? Check: {api_url}")
        print(f"  - For VM: Is the API URL correct? (localhost vs remote host)")
        print(f"  - Check network connectivity: ping/curl {api_url}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"✗ Timeout error: {e}")
        print("\n💡 The API is not responding - may be down or unreachable")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_scrape_endpoint(api_url: str, api_key: str = None, test_url: str = "https://example.com"):
    """Test scrape endpoint with a simple URL."""
    print("\n" + "="*80)
    print("TEST 3: Scrape Endpoint Test")
    print("="*80)
    
    try:
        config = Config(api_url=api_url, api_key=api_key)
        client = FirecrawlClient(config)
        
        print(f"Test URL: {test_url}")
        print("Attempting to scrape...")
        
        result = client.scrape_url(
            url=test_url,
            formats=["markdown"],
            only_main_content=True
        )
        
        if result:
            print("✓ Scrape endpoint works!")
            title = result.get("metadata", {}).get("title", "N/A")
            print(f"  Scraped page title: {title}")
            markdown_length = len(result.get("markdown", ""))
            print(f"  Markdown content length: {markdown_length} characters")
            return True
        else:
            print("✗ Scrape endpoint returned empty result")
            return False
            
    except FirecrawlConnectionError as e:
        print(f"✗ Connection error: {e}")
        return False
    except FirecrawlTimeoutError as e:
        print(f"✗ Timeout error: {e}")
        print("\n💡 The scrape request timed out (likely 408 error). This may indicate:")
        print("  - The page is too slow to load (may need >120 seconds)")
        print("  - The Firecrawl API is overloaded")
        print("  - Network connectivity issues (especially from VM)")
        print("  - Try running the test again - it will retry with longer timeouts")
        print("\n💡 Note: The scrape endpoint now retries automatically with:")
        print("  - Attempt 1: 120s timeout")
        print("  - Attempt 2: 150s timeout") 
        print("  - Attempt 3: 180s timeout")
        return False
    except FirecrawlAPIError as e:
        error_str = str(e)
        if "408" in error_str or "Request timeout" in error_str:
            print(f"✗ API timeout error (408): {e}")
            print("\n💡 This is a 408 Request Timeout error.")
            print("  The scrape endpoint should retry automatically with longer timeouts.")
            print("  If this persists, the page may be too slow or blocking requests.")
        else:
            print(f"✗ API error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        print("\n💡 Full error details:")
        traceback.print_exc()
        return False


def test_target_website_reachability(target_url: str):
    """Test if target website is accessible."""
    print("\n" + "="*80)
    print("TEST 4: Target Website Reachability")
    print("="*80)
    
    import requests
    
    print(f"Target URL: {target_url}")
    print("Testing reachability...")
    
    try:
        response = requests.get(target_url, timeout=10, allow_redirects=True)
        print(f"Status code: {response.status_code}")
        print(f"Final URL: {response.url}")
        print(f"Content length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            print("✓ Target website is accessible")
            return True
        else:
            print(f"⚠️  Website returned status {response.status_code}")
            return True  # Still accessible, just non-200 status
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error: {e}")
        print("\n💡 The target website may be down or unreachable")
        return False
    except requests.exceptions.Timeout as e:
        print(f"✗ Timeout error: {e}")
        print("\n💡 The target website is not responding")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_crawl_start(api_url: str, api_key: str = None, test_url: str = "https://example.com"):
    """Test if crawl endpoint can start a job."""
    print("\n" + "="*80)
    print("TEST 5: Crawl Endpoint Test (Starting a crawl)")
    print("="*80)
    
    try:
        config = Config(api_url=api_url, api_key=api_key)
        client = FirecrawlClient(config)
        
        print(f"Test URL: {test_url}")
        print("Starting crawl job...")
        
        job_id = client.crawl_website(
            url=test_url,
            max_depth=1,
            limit=1,
            formats=["markdown"],
            only_main_content=True
        )
        
        if job_id:
            print(f"✓ Crawl job started successfully!")
            print(f"  Job ID: {job_id}")
            
            # Check status once
            print("Checking job status...")
            time.sleep(2)
            try:
                status_data = client.get_crawl_status(job_id)
                status = status_data.get("status", "unknown")
                print(f"  Current status: {status}")
                pages = status_data.get("data", [])
                if pages:
                    print(f"  Pages found: {len(pages)}")
                return True
            except Exception as e:
                print(f"  Warning: Could not get status: {e}")
                print(f"  But job was created, which is good!")
                return True
        else:
            print("✗ Crawl endpoint did not return job ID")
            return False
            
    except FirecrawlConnectionError as e:
        print(f"✗ Connection error: {e}")
        return False
    except FirecrawlAPIError as e:
        print(f"✗ API error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test Firecrawl API connectivity and website accessibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with default settings
  python3 test_connection.py
  
  # Test with custom API URL
  python3 test_connection.py --api-url http://localhost:3002
  
  # Test with specific target website
  python3 test_connection.py --target-url https://www.wichita.edu
  
  # Test all with custom API and target
  python3 test_connection.py --api-url http://192.168.1.100:3002 --target-url https://www.wichita.edu
        """
    )
    
    parser.add_argument(
        "--api-url",
        default=None,
        help="Firecrawl API URL (defaults to env var or localhost:3002)"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Firecrawl API key (defaults to env var)"
    )
    parser.add_argument(
        "--target-url",
        default="https://example.com",
        help="Target website URL to test (default: https://example.com)"
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip scrape endpoint test"
    )
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="Skip crawl endpoint test"
    )
    parser.add_argument(
        "--skip-website",
        action="store_true",
        help="Skip target website reachability test"
    )
    
    args = parser.parse_args()
    
    # Get API URL from config or default
    config = Config(api_url=args.api_url, api_key=args.api_key)
    api_url = config.api_url
    
    print("\n" + "="*80)
    print("FIRECRAWL API CONNECTION TEST")
    print("="*80)
    print(f"API URL: {api_url}")
    print(f"Target URL: {args.target_url}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: Basic connection check
    results.append(("API Connection", test_api_connection(api_url, config.api_key)))
    
    # Test 2: Health endpoint
    results.append(("Health Endpoint", test_health_endpoint(api_url)))
    
    # Test 3: Target website reachability
    if not args.skip_website:
        results.append(("Target Website", test_target_website_reachability(args.target_url)))
    
    # Test 4: Scrape endpoint
    if not args.skip_scrape:
        results.append(("Scrape Endpoint", test_scrape_endpoint(api_url, config.api_key, args.target_url)))
    
    # Test 5: Crawl endpoint
    if not args.skip_crawl:
        results.append(("Crawl Endpoint", test_crawl_start(api_url, config.api_key, args.target_url)))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Your setup is working correctly.")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Quick test script for innovation section crawl in VM environment.
Tests the specific innovation URL to diagnose timeout issues.
"""
import sys
from firecrawl_crawler import Config, FirecrawlClient, MarkdownStorage
from firecrawl_crawler.exceptions import FirecrawlConnectionError, FirecrawlAPIError, FirecrawlTimeoutError

def test_innovation_crawl(api_url: str = None, api_key: str = None):
    """Test crawling the innovation section."""
    print("\n" + "="*80)
    print("Testing Innovation Section Crawl")
    print("="*80)
    
    innovation_url = "https://www.wichita.edu/about/innovation/"
    output_dir = "output/innovation_test"
    
    config = Config(api_url=api_url, api_key=api_key)
    client = FirecrawlClient(config)
    storage = MarkdownStorage(output_dir)
    
    print(f"\nInnovation URL: {innovation_url}")
    print(f"API URL: {config.api_url}")
    print(f"Output: {output_dir}")
    
    # Test 1: Check API connection
    print(f"\n[1/3] Checking API connection...")
    if not client.check_connection():
        print(f"✗ Cannot connect to Firecrawl API at {config.api_url}")
        print(f"\n💡 Troubleshooting:")
        print(f"  - Verify Firecrawl is running")
        print(f"  - Check network connectivity from VM")
        print(f"  - Verify API URL is accessible: curl {config.api_url}/health")
        return False
    print(f"✓ API connection successful")
    
    # Test 2: Try scraping single page first
    print(f"\n[2/3] Testing scrape of innovation page...")
    try:
        result = client.scrape_url(
            url=innovation_url,
            formats=["markdown"],
            only_main_content=True
        )
        if result:
            print(f"✓ Scrape successful!")
            title = result.get("metadata", {}).get("title", "N/A")
            print(f"  Title: {title}")
            markdown_length = len(result.get("markdown", ""))
            print(f"  Content: {markdown_length} characters")
        else:
            print(f"✗ Scrape returned empty result")
            return False
    except FirecrawlTimeoutError as e:
        print(f"✗ Scrape timed out: {e}")
        print(f"\n⚠️  The innovation page is timing out on the scrape endpoint.")
        print(f"    This is likely a server-side timeout (408).")
        print(f"\n💡 This means the page takes too long to load for the scrape endpoint.")
        print(f"    However, crawl should still work (it's async).")
        print(f"    Continuing with crawl test...")
    except Exception as e:
        print(f"✗ Scrape error: {e}")
        print(f"    Continuing with crawl test anyway...")
    
    # Test 3: Try crawl with small limit
    print(f"\n[3/3] Testing crawl of innovation section (max_depth=3, limit=5)...")
    try:
        job_id = client.crawl_website(
            url=innovation_url,
            max_depth=3,
            limit=5,  # Small limit for test
            formats=["markdown"],
            only_main_content=True
        )
        
        if job_id:
            print(f"✓ Crawl job started!")
            print(f"  Job ID: {job_id}")
            print(f"\nWaiting for crawl to complete (max 180s)...")
            
            result = client.wait_for_crawl(
                job_id=job_id,
                max_wait_time=180,  # 3 minutes for test
                poll_interval=5,
                incremental_save=storage
            )
            
            status = result.get("status", "unknown")
            pages = result.get("data", [])
            total_pages = result.get("total", 0)
            
            print(f"\nFinal status: {status}")
            print(f"Pages in data: {len(pages)}")
            print(f"Total reported: {total_pages}")
            
            if pages:
                print(f"\n✓ SUCCESS! Crawl found {len(pages)} page(s)!")
                print(f"  Pages saved to: {output_dir}")
                return True
            elif total_pages > 0:
                print(f"\n⚠️  ISSUE: API reports {total_pages} total pages, but data array is empty.")
                print(f"    This is the 'completed but no data' issue.")
                print(f"\n💡 Solutions:")
                print(f"  1. Wait a few minutes and retry:")
                print(f"     python3 diagnose_crawl.py retry {job_id} --output {output_dir}")
                print(f"  2. Check job status manually:")
                print(f"     curl {config.api_url}/v1/crawl/{job_id}")
                print(f"  3. This might be a VM network/API timing issue")
                return False
            else:
                print(f"\n⚠️  Crawl completed but found 0 pages")
                print(f"    This might mean no pages matched the criteria")
                return False
        else:
            print(f"✗ Crawl endpoint did not return job ID")
            return False
            
    except FirecrawlConnectionError as e:
        print(f"\n✗ Connection error: {e}")
        print(f"\n💡 This indicates network connectivity issues from VM to Firecrawl API.")
        return False
    except FirecrawlTimeoutError as e:
        print(f"\n✗ Timeout error: {e}")
        print(f"\n💡 The crawl timed out after 180s.")
        print(f"    This might indicate:")
        print(f"    - The crawl is taking longer than expected")
        print(f"    - Network connectivity issues from VM")
        print(f"    - The crawl is stuck in 'scraping' status")
        print(f"\n    You can check the job status later:")
        print(f"    curl {config.api_url}/v1/crawl/{job_id}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test innovation section crawl in VM")
    parser.add_argument("--api-url", default=None, help="Firecrawl API URL")
    parser.add_argument("--api-key", default=None, help="Firecrawl API key")
    
    args = parser.parse_args()
    
    success = test_innovation_crawl(args.api_url, args.api_key)
    sys.exit(0 if success else 1)


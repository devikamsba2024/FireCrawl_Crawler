"""Configuration management for Firecrawl crawler."""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class for Firecrawl crawler."""
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        output_dir: Optional[str] = None
    ):
        """
        Initialize configuration.
        
        Args:
            api_url: Firecrawl API URL (defaults to env var or localhost)
            api_key: Firecrawl API key (defaults to env var or None for local)
            output_dir: Output directory for markdown files (defaults to ./output)
        """
        self.api_url = api_url or os.getenv("FIRECRAWL_API_URL", "http://localhost:3002")
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self.output_dir = output_dir or os.getenv("OUTPUT_DIR", "./output")
        
    def get_headers(self) -> dict:
        """Get HTTP headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


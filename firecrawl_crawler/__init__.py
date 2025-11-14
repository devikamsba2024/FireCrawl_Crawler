"""Firecrawl crawler package."""
from .config import Config
from .api import FirecrawlClient
from .storage import MarkdownStorage
from .sitemap import SitemapParser
from .logger import setup_logger, get_logger
from .exceptions import (
    FirecrawlCrawlerError,
    FirecrawlAPIError,
    FirecrawlConnectionError,
    FirecrawlTimeoutError,
    StorageError,
    SitemapError,
    ConfigurationError
)

__version__ = "0.1.0"

__all__ = [
    "Config",
    "FirecrawlClient",
    "MarkdownStorage",
    "SitemapParser",
    "setup_logger",
    "get_logger",
    "FirecrawlCrawlerError",
    "FirecrawlAPIError",
    "FirecrawlConnectionError",
    "FirecrawlTimeoutError",
    "StorageError",
    "SitemapError",
    "ConfigurationError"
]


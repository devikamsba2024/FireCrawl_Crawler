"""Custom exceptions for Firecrawl crawler."""


class FirecrawlCrawlerError(Exception):
    """Base exception for Firecrawl crawler."""
    pass


class FirecrawlAPIError(FirecrawlCrawlerError):
    """Error communicating with Firecrawl API."""
    pass


class FirecrawlConnectionError(FirecrawlAPIError):
    """Cannot connect to Firecrawl instance."""
    pass


class FirecrawlTimeoutError(FirecrawlAPIError):
    """Firecrawl operation timed out."""
    pass


class StorageError(FirecrawlCrawlerError):
    """Error saving or loading files."""
    pass


class SitemapError(FirecrawlCrawlerError):
    """Error parsing or fetching sitemap."""
    pass


class ConfigurationError(FirecrawlCrawlerError):
    """Invalid configuration."""
    pass


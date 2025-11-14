"""Logging configuration for Firecrawl crawler."""
import logging
import os
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = "firecrawl_crawler", log_dir: str = "./logs", log_level: str = None) -> logging.Logger:
    """
    Set up logger with a single log file.
    
    Args:
        name: Logger name
        log_dir: Directory to store log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). If None, reads from LOG_LEVEL env var
        
    Returns:
        Configured logger instance
    """
    # Determine log level from env var or parameter
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    else:
        log_level = log_level.upper()
    
    # Map string to logging level
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    log_level_int = level_map.get(log_level, logging.INFO)
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level_int)
    
    # Prevent duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler - matches the configured log level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_int)  # Use same level as file
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # Single File Handler
    # Logs everything at the configured level and above
    file_handler = RotatingFileHandler(
        log_path / 'crawler.log',
        maxBytes=20*1024*1024,  # 20MB
        backupCount=5
    )
    file_handler.setLevel(log_level_int)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Log startup message
    logger.info("="*70)
    logger.info(f"Logging initialized - Level: {log_level} - File: {log_path / 'crawler.log'}")
    logger.info("="*70)
    
    return logger


def get_logger(name: str = "firecrawl_crawler") -> logging.Logger:
    """
    Get an existing logger or create a new one.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


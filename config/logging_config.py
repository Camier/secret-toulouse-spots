#!/usr/bin/env python3
"""
Centralized logging configuration for Secret Toulouse Spots
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
import json


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'scraper'):
            log_data['scraper'] = record.scraper
        if hasattr(record, 'url'):
            log_data['url'] = record.url
        if hasattr(record, 'error_type'):
            log_data['error_type'] = record.error_type
        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration
            
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


def setup_logging(
    name: str = None,
    level: str = "INFO",
    log_dir: str = "logs",
    console: bool = True,
    file: bool = True,
    structured: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        name: Logger name (None for root logger)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        console: Enable console output
        file: Enable file output
        structured: Use JSON structured logging
        max_bytes: Max size per log file
        backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        if structured:
            console_formatter = StructuredFormatter()
        else:
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file:
        # Determine log file name
        if name:
            log_file = log_path / f"{name}.log"
        else:
            log_file = log_path / "toulouse_spots.log"
            
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        
        if structured:
            file_formatter = StructuredFormatter()
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Error file handler (always enabled for ERROR+)
    error_file = log_path / "errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s\n%(exc_info)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(error_handler)
    
    return logger


# Convenience functions for structured logging
class LoggerAdapter(logging.LoggerAdapter):
    """Adapter for adding contextual information to logs"""
    
    def process(self, msg, kwargs):
        # Add extra context from adapter
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)
        return msg, kwargs


def get_scraper_logger(scraper_name: str, **context) -> LoggerAdapter:
    """Get a logger adapter for a specific scraper with context"""
    logger = setup_logging(f"scraper.{scraper_name}")
    return LoggerAdapter(logger, {"scraper": scraper_name, **context})


def log_performance(logger: logging.Logger, operation: str):
    """Context manager for logging operation performance"""
    import time
    from contextlib import contextmanager
    
    @contextmanager
    def _log_performance():
        start_time = time.time()
        logger.info(f"Starting {operation}")
        try:
            yield
        finally:
            duration = time.time() - start_time
            logger.info(
                f"Completed {operation}",
                extra={"duration": duration, "operation": operation}
            )
    
    return _log_performance()


def log_scraping_stats(logger: logging.Logger, stats: dict):
    """Log scraping statistics in a structured way"""
    logger.info(
        "Scraping statistics",
        extra={
            "stats": stats,
            "total_spots": stats.get("total", 0),
            "success_rate": stats.get("success_rate", 0),
            "errors": stats.get("errors", 0)
        }
    )


# Configure root logger on import
root_logger = setup_logging(level="INFO")

# Reduce noise from third-party libraries
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
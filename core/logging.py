"""
Structured logging configuration for the second-hand research agent.

Provides human-readable logging by default, with optional JSON formatting
for debug/structured logging mode.
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import json


class JSONFormatter(logging.Formatter):
    """
    Custom log formatter that outputs JSON.
    
    Each log record is formatted as a JSON object on a single line.
    Used when --debug flag is set or when structured logging is needed.
    """
    
    def __init__(self, include_timestamp: bool = True, include_level: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_data: Dict[str, Any] = {
            "message": record.getMessage(),
        }
        
        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        if self.include_level:
            log_data["level"] = record.levelname
        
        # Add module name
        if hasattr(record, 'module_name') and record.module_name:
            log_data["module"] = record.module_name
        else:
            # Extract module from pathname
            log_data["module"] = record.module
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in (
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName',
                'relativeCreated', 'stack_info', 'exc_info', 'exc_text',
                'thread', 'threadName', 'taskName', 'module_name'
            ):
                try:
                    # Ensure value is JSON serializable
                    if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                        log_data[key] = value
                    else:
                        log_data[key] = str(value)
                except (TypeError, ValueError):
                    log_data[key] = str(value)
        
        # Handle exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
            }
        
        return json.dumps(log_data, default=str)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable log formatter for clear, transparent logging.
    
    Produces output like:
    [pipeline] Scraping complete (listing_count=292)
    [filter] Pass 1: 292 -> 150 listings
    [processor] Fetching descriptions for 150 listings
    [ERROR] Failed to fetch URL: http://...
    """
    
    def __init__(self):
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record in a human-readable way."""
        # Get the module name - use the logger name, cleaned up
        module = record.name
        
        # Clean up module name if it's a full path
        if module and '.' in module:
            # Extract the last part (e.g., "core.pipeline" -> "pipeline")
            module = module.split('.')[-1]
        
        # Get the message
        message = record.getMessage()
        
        # Get log level indicator - only show for non-INFO levels to keep output clean
        level_indicator = {
            'DEBUG': '[DEBUG]',
            'INFO': '',
            'WARNING': '[WARN]',
            'ERROR': '[ERROR]',
            'CRITICAL': '[CRITICAL]',
        }.get(record.levelname, f'[{record.levelname}]')
        
        # Build the prefix with module and level
        prefix = f"[{module}] {level_indicator} " if module else f"{level_indicator} "
        
        # Format extra fields - only include important ones for readability
        important_keys = ['listing_count', 'duplicates_removed', 'filtered', 'removed', 
                        'kept', 'discarded', 'model', 'error', 'query', 'stage',
                        'pass_num', 'filter', 'module_count', 'filter_type', 'final_listing_count',
                        'error_count', 'original_query', 'cleaned_query']
        
        extra_parts = []
        for key, value in record.__dict__.items():
            if key in important_keys:
                try:
                    extra_parts.append(f"{key}={value}")
                except (TypeError, ValueError):
                    extra_parts.append(f"{key}={str(value)}")
        
        if extra_parts:
            extra_str = " (" + ", ".join(extra_parts) + ")"
        else:
            extra_str = ""
        
        # Combine everything
        return f"{prefix}{message}{extra_str}"


def setup_logger(
    name: str,
    level: int = logging.INFO,
    json_format: bool = False,
    module_name: Optional[str] = None,
) -> logging.Logger:
    """
    Set up a logger with structured (JSON) or human-readable formatting.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use JSON formatter; otherwise use human-readable
        module_name: Optional module name to include in logs
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Set formatter - use JSON only if explicitly requested, otherwise human-readable
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = HumanReadableFormatter()
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Set module name for formatter
    if module_name:
        logger.module_name = module_name
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str, module_name: Optional[str] = None, json_format: bool = False) -> logging.Logger:
    """
    Get a logger with human-readable formatting for module logging.
    
    This is the main function to use for getting loggers in modules.
    By default uses clear, human-readable formatting. Pass json_format=True
    for structured JSON logging (useful for debugging or machine parsing).
    
    Args:
        name: Logger name (typically __name__)
        module_name: Optional module name to include in logs
        json_format: If True, use JSON formatting; otherwise human-readable
        
    Returns:
        Configured logger
    """
    return setup_logger(name, json_format=json_format, module_name=module_name)


def get_console_logger(name: str = "console") -> logging.Logger:
    """
    Get a logger for console output (human-readable).
    
    Use this for user-facing messages.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger with human-readable formatting
    """
    return setup_logger(name, json_format=False)





# Configure root logger to use human-readable formatting by default
root_logger = logging.getLogger()
if not root_logger.handlers:
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(HumanReadableFormatter())
    root_logger.addHandler(handler)

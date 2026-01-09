"""
Centralized logging utility for WorkAlign
Provides structured logging with different levels and easy debugging
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Configure logging format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def get_logger(name: str, level: str = 'INFO', log_to_file: bool = True):
    """
    Get a configured logger instance

    Args:
        name: Logger name (usually __name__ from calling module)
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_to_file: Whether to also write logs to file

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, level.upper()))

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler (if enabled)
        if log_to_file:
            log_file = LOG_DIR / f"workalign_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

    return logger


# Convenience function for debug logging with context
def log_analysis_step(logger, step_name: str, data: dict = None):
    """
    Log an analysis step with optional data

    Args:
        logger: Logger instance
        step_name: Name of the analysis step
        data: Optional dict of data to log
    """
    logger.info(f"=== {step_name} ===")
    if data:
        for key, value in data.items():
            logger.debug(f"  {key}: {value}")


# Convenience function for logging performance metrics
def log_performance(logger, operation: str, duration_seconds: float):
    """
    Log performance metrics

    Args:
        logger: Logger instance
        operation: Name of the operation
        duration_seconds: Duration in seconds
    """
    logger.info(f"Performance: {operation} took {duration_seconds:.3f}s")


# Convenience function for logging errors with context
def log_error_with_context(logger, error: Exception, context: dict = None):
    """
    Log an error with optional context

    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Optional dict of contextual information
    """
    logger.error(f"Error: {str(error)}")
    if context:
        logger.error("Context:")
        for key, value in context.items():
            logger.error(f"  {key}: {value}")
    logger.exception("Stack trace:")

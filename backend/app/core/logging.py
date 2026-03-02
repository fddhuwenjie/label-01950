"""
Logging configuration using loguru.
"""
import sys
from loguru import logger


def setup_logging(debug: bool = False) -> None:
    """
    Configure application logging.
    
    Args:
        debug: Enable debug level logging if True.
    """
    # Remove default handler
    logger.remove()
    
    # Console handler
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if debug else "INFO",
        colorize=True,
    )
    
    # File handler for errors
    logger.add(
        "logs/error.log",
        format=log_format,
        level="ERROR",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )
    
    # File handler for all logs
    logger.add(
        "logs/app.log",
        format=log_format,
        level="DEBUG" if debug else "INFO",
        rotation="50 MB",
        retention="30 days",
        compression="zip",
    )
    
    logger.info("Logging configured successfully")


__all__ = ["logger", "setup_logging"]

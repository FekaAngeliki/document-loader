"""
Logging configuration for Document Loader
"""
import logging
from typing import List

def configure_app_logging(verbose: bool = False):
    """Configure application logging."""
    # Set app-specific loggers to appropriate levels
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Application loggers
    app_loggers = [
        'src',
        'document_loader',
        'batch_runner',
        'file_processor',
        'change_detector',
        'scanner',
    ]
    
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
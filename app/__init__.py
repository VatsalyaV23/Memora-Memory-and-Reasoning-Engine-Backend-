"""Org Memory Engine - Application Package"""

__version__ = "1.0.0"
__author__ = "Org Memory Team"

# Initialize app on import
import logging

logger = logging.getLogger(__name__)

def init_app():
    """Initialize the application"""
    logger.info("Initializing Org Memory Engine...")
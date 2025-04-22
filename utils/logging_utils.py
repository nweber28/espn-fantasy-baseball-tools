"""
Logging utilities for the application.
"""
import logging
import streamlit as st

def setup_logging():
    """
    Configure logging for the application.
    
    Returns:
        Logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    return logger

import logging
import sys
from pathlib import Path

def setup_logging(log_level: int = logging.INFO) -> None:
    """
    Set up logging configuration with both file and console handlers.
    
    Args:
        log_level: The logging level to use (default: logging.INFO)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    root_logger.handlers = []
    
    # File handler with detailed format
    file_handler = logging.FileHandler(log_dir / 'downloader.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(file_handler)
    
    # Console handler with simpler format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Ensure yt-dlp's output is also captured
    yt_dlp_logger = logging.getLogger('yt_dlp')
    yt_dlp_logger.setLevel(log_level)
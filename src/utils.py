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
    
    # File handler with UTF-8 encoding and detailed format
    file_handler = logging.FileHandler(log_dir / 'downloader.log', encoding='utf-8', errors='replace')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)
    
    # Console handler with UTF-8 encoding and simpler format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.encoding = 'utf-8'
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # Force immediate output
    root_logger.propagate = False
    
    # Ensure yt-dlp's output is also captured
    yt_dlp_logger = logging.getLogger('yt_dlp')
    yt_dlp_logger.setLevel(log_level)
    
    # Disable other loggers that might interfere
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
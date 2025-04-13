"""
Video to MP3 downloader package
"""

from .downloader import VideoDownloader
from .utils import setup_logging

__all__ = ['VideoDownloader', 'setup_logging']
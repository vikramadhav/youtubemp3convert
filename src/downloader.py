import os
import logging
import shutil
from typing import Optional
import yt_dlp
from pathlib import Path
import time
import hashlib

class VideoDownloader:
    def __init__(self, output_dir: str = 'downloads', max_retries: int = 3):
        self.output_dir = Path(output_dir)
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self._check_dependencies()
        self._setup_output_dir()
        self._configure_yt_dlp()
        self.downloaded_files = set()

    def _check_dependencies(self):
        """Check if FFmpeg is installed and accessible."""
        if not shutil.which('ffmpeg'):
            error_msg = (
                "FFmpeg is not installed or not in PATH. "
                "Please install FFmpeg:\n"
                "Windows: Download from https://ffmpeg.org/download.html and add to PATH\n"
                "Linux: sudo apt install ffmpeg\n"
                "macOS: brew install ffmpeg"
            )
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def _setup_output_dir(self):
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _configure_yt_dlp(self):
        """Configure yt-dlp options with filename template."""
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'logger': self.logger,
            'progress_hooks': [self._download_hook],
            'verbose': True,
            'ignoreerrors': True,  # Skip unavailable videos in playlists
        }

    def _get_file_hash(self, filepath: Path) -> str:
        """Calculate MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _is_duplicate(self, filepath: Path) -> bool:
        """Check if a file is a duplicate based on content hash."""
        if not filepath.exists():
            return False
        
        new_hash = self._get_file_hash(filepath)
        
        # Check if this hash exists in our downloaded files
        for existing_file in self.output_dir.glob('*.mp3'):
            if existing_file != filepath and self._get_file_hash(existing_file) == new_hash:
                self.logger.info(f"Duplicate found: {filepath.name} matches {existing_file.name}")
                return True
        return False

    def _download_hook(self, d):
        """Progress hook for downloads."""
        if d['status'] == 'downloading':
            if 'downloaded_bytes' in d and 'total_bytes' in d:
                progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                self.logger.info(f"Download progress: {progress:.1f}%")
        elif d['status'] == 'finished':
            filepath = Path(d['filename'])
            if filepath.suffix == '.mp3':
                if self._is_duplicate(filepath):
                    self.logger.warning(f"Removing duplicate file: {filepath.name}")
                    filepath.unlink()
                else:
                    self.downloaded_files.add(filepath)

    def _download_with_retry(self, url: str, is_playlist: bool = False) -> bool:
        """Download with retry logic and duplicate checking."""
        for attempt in range(self.max_retries):
            try:
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    self.logger.info(f"Download attempt {attempt + 1}/{self.max_retries}")
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        self.logger.error(f"Could not extract info for URL: {url}")
                        return False
                    
                    # For playlists, handle each video separately
                    if is_playlist and 'entries' in info:
                        success = False
                        for entry in info['entries']:
                            if entry:
                                video_url = entry['webpage_url']
                                try:
                                    ydl.download([video_url])
                                    success = True
                                except Exception as e:
                                    self.logger.error(f"Error downloading playlist video {video_url}: {str(e)}")
                                    # Continue with next video
                                    continue
                        return success
                    else:
                        ydl.download([url])
                return True
                
            except yt_dlp.utils.DownloadError as e:
                if "Video unavailable" in str(e) or "Private video" in str(e):
                    self.logger.warning(f"Video not available, skipping: {url}")
                    return False
                elif attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Max retries reached for URL: {url}")
                    return False
            except Exception as e:
                self.logger.error(f"Error during download (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.error("Max retries reached. Download failed.")
                    return False

    def download_single(self, url: str) -> bool:
        """Download a single video and convert to MP3."""
        self.logger.info(f"Starting download of video: {url}")
        return self._download_with_retry(url)

    def download_playlist(self, url: str) -> bool:
        """Download all videos from a playlist and convert to MP3."""
        self.logger.info(f"Starting download of playlist: {url}")
        return self._download_with_retry(url, is_playlist=True)
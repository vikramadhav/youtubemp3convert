import os
import logging
import shutil
from typing import Optional
import yt_dlp
from pathlib import Path
import time
import hashlib
import subprocess
from .online_converter import OnlineConverter

class VideoDownloader:
    def __init__(self, output_dir: str = 'downloads', max_retries: int = 3):
        self.output_dir = Path(output_dir)
        self.unprocessed_dir = self.output_dir / 'unprocessed'
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self._check_dependencies()
        self._setup_output_dir()
        self._configure_yt_dlp()
        self.downloaded_files = set()
        self.skipped_ads_count = 0  # Track number of skipped ads
        self.online_converter = OnlineConverter()

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
        """Create output and unprocessed directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.unprocessed_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize the filename by removing special characters and excess whitespace.
        
        Args:
            filename: The original filename
            
        Returns:
            Sanitized filename safe for all operating systems
        """
        # First, get the name and extension separately
        name, ext = os.path.splitext(filename)
        
        # Convert fullwidth characters to normal width
        import unicodedata
        name = unicodedata.normalize('NFKC', name)
        
        # Remove or replace special characters
        import re
        # Remove quotes and special characters at start/end
        name = re.sub(r'^[\'"""＂]+|[\'"""＂]+$', '', name)
        # Replace spaces and special chars with underscore
        name = re.sub(r'[^\w\s-]', '', name)
        # Replace multiple spaces with single underscore
        name = re.sub(r'\s+', '_', name.strip())
        # Remove any remaining invalid characters
        name = re.sub(r'[-_]+', '_', name)
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        # If name is empty after sanitization, use a default name
        if not name:
            name = "audio"
            
        # Combine name and extension
        return f"{name}{ext}"

    def _configure_yt_dlp(self):
        """Configure yt-dlp options with filename template."""
        self.ydl_opts = {
            'format': 'bestaudio[acodec=mp3]/bestaudio[acodec=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
            'writethumbnail': False,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'logger': self.logger,
            'progress_hooks': [self._download_hook],
            'verbose': True,
            'ignoreerrors': False,
            'extract_flat': False,
            'force_progress': True,
            'noplaylist': True,
            'retries': 5,
            'fragment_retries': 5,
            'skip_unavailable_fragments': True,
            'continuedl': True,
            'no_check_formats': False,
            'match_filter': self._ad_filter,
            'socket_timeout': 30,
            'extractor_retries': 5,
            'prepare_filename': self._sanitize_filename,
            'ffmpeg_location': shutil.which('ffmpeg'),
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'postprocessor_args': {
                'FFmpegExtractAudio': [
                    '-codec:a', 'libmp3lame',
                    '-ar', '44100',
                    '-ac', '2',
                    '-b:a', '192k',
                    '-joint_stereo', '1',
                    '-af', 'aresample=async=1:first_pts=0'
                ],
            }
        }

    def _ad_filter(self, info_dict):
        """Filter out advertisements and sponsorship segments."""
        # Check various indicators of an advertisement
        if any([
            info_dict.get('is_ad', False),
            info_dict.get('ad_flag', False),
            'advertisement' in str(info_dict.get('title', '')).lower(),
            'sponsor' in str(info_dict.get('title', '')).lower(),
            info_dict.get('duration', 0) < 10,  # Very short videos are likely ads
            info_dict.get('channel_id', '') in ['UCbMScGQ8jGRogxS8PyCM8uA'],  # Known ad channel IDs
            any(tag in str(info_dict.get('tags', [])).lower() for tag in ['ad', 'advertisement', 'sponsor']),
            info_dict.get('live_status', '') == 'is_live'  # Skip live streams
        ]):
            self.logger.info("Skipping advertisement or sponsored content")
            self.skipped_ads_count += 1
            return "Ad content detected and skipped"
        return None

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

    def _try_online_conversion(self, url: str, output_path: Path) -> bool:
        """Attempt conversion using online service when local conversion fails."""
        try:
            return self.online_converter.convert_to_mp3(url, output_path)
        except Exception as e:
            self.logger.error(f"Online conversion error: {str(e)}")
            return False

    def _convert_to_mp3(self, input_path: Path, output_path: Path) -> bool:
        """Convert audio file to MP3 format using FFmpeg."""
        try:
            cmd = [
                'ffmpeg',
                '-y',
                '-i', str(input_path),
                '-vn',
                '-acodec', 'libmp3lame',
                '-ar', '44100',
                '-ac', '2',
                '-b:a', '192k',
                '-map_metadata', '0:s:0',
                '-id3v2_version', '3',
                '-write_xing', '1',
                str(output_path)
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.logger.error(f"FFmpeg conversion error: {stderr}")
                raise subprocess.CalledProcessError(
                    process.returncode, cmd,
                    output=stdout, stderr=stderr
                )
                
            self.logger.info(f"Successfully converted to mp3: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error converting to mp3: {str(e)}")
            return False

    def _download_hook(self, d):
        """Progress hook for downloads."""
        status = d.get('status', '')
        
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            
            if total > 0:
                progress = (downloaded / total) * 100
                speed = d.get('speed', 0)
                if speed:
                    eta = d.get('eta', 'N/A')
                    self.logger.info(f"Download progress: {progress:.1f}% (Speed: {speed/1024:.1f}KB/s, ETA: {eta}s)")
                else:
                    self.logger.info(f"Download progress: {progress:.1f}%")
            
        elif status == 'finished':
            filepath = Path(d['filename'])
            self.logger.info(f"Download finished: {filepath.name}")
            
            try:
                # Check if file needs conversion (not already MP3)
                if filepath.suffix.lower() != '.mp3':
                    self.logger.info(f"Converting audio to mp3: {filepath.name}")
                    output_path = filepath.with_suffix('.mp3')
                    
                    if self._convert_to_mp3(filepath, output_path):
                        if filepath.exists():
                            filepath.unlink()  # Remove original only after successful conversion
                        filepath = output_path
                    else:
                        # Try online conversion as fallback only if local conversion failed
                        original_url = d.get('info_dict', {}).get('webpage_url', '')
                        if original_url:
                            self.logger.info("Attempting online conversion as fallback...")
                            if self.online_converter.convert_to_mp3(original_url, output_path):
                                self.logger.info("Online conversion successful")
                                if filepath.exists():
                                    filepath.unlink()
                                filepath = output_path
                            else:
                                self.logger.error("Online conversion failed")
                                if filepath.exists():
                                    try:
                                        unprocessed_path = self.unprocessed_dir / filepath.name
                                        shutil.move(str(filepath), str(unprocessed_path))
                                        self.logger.info(f"Moved unconverted file to: {unprocessed_path}")
                                    except Exception as move_error:
                                        self.logger.error(f"Error moving unconverted file: {str(move_error)}")
                
                # Process the final file
                if filepath.exists():
                    if filepath.suffix.lower() == '.mp3':
                        if self._is_duplicate(filepath):
                            self.logger.warning(f"Removing duplicate file: {filepath.name}")
                            filepath.unlink()
                        else:
                            self.downloaded_files.add(filepath)
                            self.logger.info(f"Successfully processed: {filepath.name}")
                    else:
                        # Move non-MP3 files to unprocessed
                        unprocessed_path = self.unprocessed_dir / filepath.name
                        shutil.move(str(filepath), str(unprocessed_path))
                        self.logger.info(f"Moved non-MP3 file to: {unprocessed_path}")
                        
            except Exception as e:
                self.logger.error(f"Error processing downloaded file: {str(e)}")
                # Preserve the original file in case of error
                if filepath.exists() and filepath.suffix.lower() != '.mp3':
                    try:
                        unprocessed_path = self.unprocessed_dir / filepath.name
                        shutil.move(str(filepath), str(unprocessed_path))
                        self.logger.info(f"Moved original file to unprocessed after error: {unprocessed_path}")
                    except Exception as move_error:
                        self.logger.error(f"Error moving original file: {str(move_error)}")
            
        elif status == 'error':
            error = d.get('error', 'Unknown error')
            self.logger.error(f"Download error: {error}")

    def _download_with_retry(self, url: str, is_playlist: bool = False) -> bool:
        """Download with retry logic and duplicate checking."""
        self.skipped_ads_count = 0  # Reset counter for new download
        for attempt in range(self.max_retries):
            try:
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    self.logger.info(f"Download attempt {attempt + 1}/{self.max_retries}")
                    try:
                        self.logger.info(f"Extracting video info from URL: {url}")
                        info = ydl.extract_info(url, download=True)  # Changed to True for direct download
                        
                        if not info:
                            self.logger.error(f"Could not extract info for URL: {url}")
                            return False
                        
                        # Log successful download
                        if 'title' in info:
                            self.logger.info(f"Successfully downloaded: {info['title']}")
                            return True
                        else:
                            self.logger.error("Download completed but no title found in info")
                            return False
                            
                    except yt_dlp.utils.DownloadError as e:
                        error_msg = str(e).lower()
                        self.logger.error(f"Download error details: {error_msg}")
                        
                        if any(msg in error_msg for msg in ["private video", "sign in", "premium", "members only"]):
                            self.logger.warning(f"Skipping private/members-only video: {url}")
                            return False
                        elif "copyright" in error_msg:
                            self.logger.warning(f"Skipping copyrighted/unavailable video: {url}")
                            return False
                        elif "advertisement" in error_msg:
                            self.logger.info(f"Skipping advertisement: {url}")
                            self.skipped_ads_count += 1
                            return True
                        raise
                
            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e).lower()
                self.logger.error(f"Attempt {attempt + 1} failed with error: {str(e)}")
                
                if "video unavailable" in error_msg:
                    self.logger.warning(f"Video not available, skipping: {url}")
                    return False
                elif "private video" in error_msg or "sign in" in error_msg:
                    self.logger.warning(f"Private video, skipping: {url}")
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
#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.downloader import VideoDownloader
from src.utils import setup_logging

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Download videos and convert to MP3')
    parser.add_argument('url', help='URL of the video or playlist to download')
    parser.add_argument('-o', '--output-dir', default='downloads',
                       help='Directory to save downloaded files')
    parser.add_argument('--max-retries', type=int, default=3,
                       help='Maximum number of retry attempts')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize downloader
        downloader = VideoDownloader(
            output_dir=args.output_dir,
            max_retries=args.max_retries
        )
        
        # Detect if URL is a playlist
        if 'playlist' in args.url.lower():
            logger.info('Detected playlist URL')
            success = downloader.download_playlist(args.url)
        else:
            logger.info('Detected single video URL')
            success = downloader.download_single(args.url)
        
        if success:
            logger.info('Download completed successfully')
        else:
            logger.error('Download failed')
            exit(1)
            
    except Exception as e:
        logger.error(f'An error occurred: {str(e)}')
        exit(1)

if __name__ == '__main__':
    main()
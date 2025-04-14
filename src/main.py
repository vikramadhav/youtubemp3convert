#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.downloader import VideoDownloader
from src.utils import setup_logging

def process_url(url: str, downloader: VideoDownloader, logger: logging.Logger) -> bool:
    # Process single URL or playlist
    if '&list=' in url or '?list=' in url:
        logger.info(f'Detected playlist URL: {url}')
        return downloader.download_playlist(url)
    else:
        logger.info(f'Detected single video URL: {url}')
        return downloader.download_single(url)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Download videos and convert to MP3')
    parser.add_argument('url', nargs='?', help='URL of the video or playlist to download')
    parser.add_argument('-i', '--input-file', help='Input file containing URLs (one per line)')
    parser.add_argument('-o', '--output-dir', default='downloads',
                       help='Directory to save downloaded files')
    parser.add_argument('--max-retries', type=int, default=3,
                       help='Maximum number of retry attempts')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging with appropriate level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize downloader
        downloader = VideoDownloader(
            output_dir=args.output_dir,
            max_retries=args.max_retries
        )
        
        if args.url:
            # Process single URL from command line
            success = process_url(args.url, downloader, logger)
        else:
            # Use default input.txt in project root if no URL provided
            input_file = Path(args.input_file if args.input_file else project_root / 'input.txt')
            
            if not input_file.exists():
                logger.error(f'Input file not found: {input_file}')
                exit(1)
                
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f 
                           if line.strip() and not line.strip().startswith(('#', '##'))]
                
                if not urls:
                    logger.error(f'No valid URLs found in {input_file}')
                    exit(1)
                
                logger.info(f'Found {len(urls)} valid URLs in {input_file}')
                success = True
                
                for i, url in enumerate(urls, 1):
                    logger.info(f'Processing URL {i}/{len(urls)}')
                    if not process_url(url, downloader, logger):
                        success = False
                        logger.error(f'Failed to process URL: {url}')
                
            except Exception as e:
                logger.error(f'Error reading input file: {str(e)}')
                exit(1)
        
        if success:
            logger.info('All downloads completed successfully')
        else:
            logger.error('Some downloads failed')
            exit(1)
            
    except Exception as e:
        logger.error(f'An error occurred: {str(e)}')
        if args.verbose:
            logger.exception("Detailed error information:")
        exit(1)

if __name__ == '__main__':
    main()
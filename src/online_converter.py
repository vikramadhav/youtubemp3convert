import requests
import json
import time
from pathlib import Path
import logging
from typing import Optional

class OnlineConverter:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://api.ytbapi.com/api/convert"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def convert_to_mp3(self, video_url: str, output_path: Path) -> bool:
        """
        Convert video to MP3 using online converter API.
        
        Args:
            video_url: YouTube video URL
            output_path: Path to save the MP3 file
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        try:
            # Initialize conversion
            payload = {"url": video_url, "format": "mp3"}
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get("success"):
                self.logger.error(f"Failed to initialize conversion: {data.get('error', 'Unknown error')}")
                return False
                
            download_url = data.get("download_url")
            if not download_url:
                self.logger.error("No download URL received from converter")
                return False

            # Download the converted file
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = requests.get(download_url, stream=True)
                    response.raise_for_status()
                    
                    # Save the file
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    self.logger.info(f"Successfully downloaded converted file to {output_path}")
                    return True
                    
                except requests.RequestException as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count
                        self.logger.warning(f"Download failed, retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        self.logger.error(f"Failed to download converted file after {max_retries} attempts: {str(e)}")
                        return False

        except requests.RequestException as e:
            self.logger.error(f"Error during online conversion: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during online conversion: {str(e)}")
            return False
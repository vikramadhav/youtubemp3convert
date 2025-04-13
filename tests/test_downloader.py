import unittest
from unittest.mock import patch, MagicMock
import os
from pathlib import Path
from src.downloader import VideoDownloader

class TestVideoDownloader(unittest.TestCase):
    def setUp(self):
        self.test_output_dir = "test_downloads"
        self.downloader = VideoDownloader(output_dir=self.test_output_dir)

    def tearDown(self):
        # Clean up test directory if it exists
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)

    @patch('yt_dlp.YoutubeDL')
    def test_download_single(self, mock_yt_dlp):
        # Arrange
        test_url = "https://example.com/video"
        mock_yt_dlp.return_value.__enter__.return_value.download.return_value = 0

        # Act
        result = self.downloader.download_single(test_url)

        # Assert
        self.assertTrue(result)
        mock_yt_dlp.return_value.__enter__.return_value.download.assert_called_once_with([test_url])

    @patch('yt_dlp.YoutubeDL')
    def test_download_with_retry(self, mock_yt_dlp):
        # Arrange
        test_url = "https://example.com/video"
        mock_yt_dlp.return_value.__enter__.return_value.download.side_effect = [
            Exception("Download failed"),
            0  # Second attempt succeeds
        ]

        # Act
        result = self.downloader.download_single(test_url)

        # Assert
        self.assertTrue(result)
        self.assertEqual(
            mock_yt_dlp.return_value.__enter__.return_value.download.call_count,
            2
        )

    def test_output_directory_creation(self):
        # Arrange & Act
        test_dir = Path(self.test_output_dir)
        
        # Assert
        self.assertTrue(test_dir.exists())
        self.assertTrue(test_dir.is_dir())

if __name__ == '__main__':
    unittest.main()
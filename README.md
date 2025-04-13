# Video to MP3 Downloader

A Python tool for downloading videos and converting them to MP3 format, with support for both single videos and playlists.

## Features

- Download single videos and convert to MP3
- Support for playlist downloads
- Built-in retry mechanism with exponential backoff
- Progress tracking and logging
- High-quality audio extraction (192kbps MP3)

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Download a single video:
```bash
python src/main.py "VIDEO_URL" -o downloads
```

### Download a playlist:
```bash
python src/main.py "PLAYLIST_URL" -o downloads
```

### Command-line options:
- `url`: URL of the video or playlist (required)
- `-o, --output-dir`: Output directory for downloaded files (default: 'downloads')
- `--max-retries`: Maximum number of retry attempts (default: 3)

## Logging

Logs are stored in the `logs` directory. Both console and file logging are enabled by default.
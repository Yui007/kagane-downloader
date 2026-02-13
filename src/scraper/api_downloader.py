"""
API-based Chapter Downloader
Captures image URLs from network requests and downloads them directly
"""

import re
import json
import time
import requests
from pathlib import Path
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from .api_models import Book, Series


@dataclass
class DownloadResult:
    """Result of a chapter download"""
    book: Book
    success: bool
    chapter_dir: Path
    pages_downloaded: int
    error: Optional[str] = None


class APIChapterDownloader:
    """
    Downloads chapter images using captured network URLs.
    
    The approach:
    1. Open the reader page in a browser
    2. Capture network requests to get image URLs from akari.kagane.org
    3. Download images directly using requests
    """
    
    IMAGE_URL_PATTERN = "akari.kagane.org/api/v2/books/file/"
    
    def __init__(
        self,
        download_dir: Path,
        max_concurrent_images: int = 10,
        max_retries: int = 3,
        request_timeout: int = 30
    ):
        self.download_dir = download_dir
        self.max_concurrent_images = max_concurrent_images
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        
        # Create a session for downloading
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://kagane.org/"
        })
    
    @staticmethod
    def sanitize_filename(name: str, max_length: int = 80) -> str:
        """Sanitize a string to be safe for Windows filenames"""
        sanitized = re.sub(r'[<>:"/\\|?*~\[\]{}]', '_', name)
        sanitized = re.sub(r'_+', '_', sanitized)
        sanitized = sanitized.strip(' _')
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip(' _')
        return sanitized
    
    def download_image(self, url: str, output_path: Path) -> bool:
        """Download a single image with retries"""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.request_timeout, stream=True)
                response.raise_for_status()
                
                # Determine file extension from content-type or URL
                content_type = response.headers.get('content-type', '')
                if 'webp' in content_type:
                    ext = '.webp'
                elif 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'
                elif 'png' in content_type:
                    ext = '.png'
                else:
                    # Try to get from URL
                    if '.webp' in url.lower():
                        ext = '.webp'
                    elif '.jpg' in url.lower() or '.jpeg' in url.lower():
                        ext = '.jpg'
                    elif '.png' in url.lower():
                        ext = '.png'
                    else:
                        ext = '.webp'  # Default to webp
                
                # Update path with correct extension
                final_path = output_path.with_suffix(ext)
                
                with open(final_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                return True
                
            except Exception:
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                continue
        
        return False
    
    def download_from_urls(
        self,
        image_urls: list[str],
        output_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> int:
        """
        Download images from a list of URLs.
        
        Args:
            image_urls: List of image URLs to download
            output_dir: Directory to save images
            progress_callback: Optional callback(current, total)
        
        Returns:
            Number of successfully downloaded images
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        total = len(image_urls)
        downloaded = 0
        
        # Sort URLs to maintain page order
        sorted_urls = sorted(image_urls)
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent_images) as executor:
            futures = {}
            
            for idx, url in enumerate(sorted_urls, 1):
                output_path = output_dir / f"{idx:03d}"
                future = executor.submit(self.download_image, url, output_path)
                futures[future] = idx
            
            for future in as_completed(futures):
                if future.result():
                    downloaded += 1
                    if progress_callback:
                        progress_callback(downloaded, total)
        
        return downloaded
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_reader_url(series_id: str, book_id: str) -> str:
    """Generate the reader URL for a book"""
    return f"https://kagane.org/series/{series_id}/reader/{book_id}"


def get_image_urls_from_browser(
    driver,
    series_id: str,
    book_id: str,
    wait_time: int = 15
) -> list[str]:
    """
    Capture image URLs from browser network logs.
    
    Args:
        driver: Selenium webdriver with Network logging enabled
        series_id: Series UUID
        book_id: Book UUID
        wait_time: Time to wait for images to load
    
    Returns:
        List of image URLs
    """
    reader_url = get_reader_url(series_id, book_id)
    
    # Navigate to reader
    driver.get(reader_url)
    
    # Wait for images to load
    time.sleep(wait_time)
    
    # Get network logs
    logs = driver.get_log("performance")
    
    image_urls = set()
    
    for entry in logs:
        try:
            log = json.loads(entry["message"])["message"]
            
            if log["method"] == "Network.requestWillBeSent":
                url = log["params"]["request"]["url"]
                
                if APIChapterDownloader.IMAGE_URL_PATTERN in url:
                    image_urls.add(url)
        except (json.JSONDecodeError, KeyError):
            continue
    
    return list(image_urls)

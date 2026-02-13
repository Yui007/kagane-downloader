"""
Download Worker - Background thread for downloading chapters using API
"""

import sys
import json
import time
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import get_config
from src.scraper import Series, Book
from src.scraper.api_downloader import APIChapterDownloader, get_reader_url
from src.scraper.browser import BrowserManager
from src.converter import create_pdf, create_cbz


class DownloadWorker(QThread):
    """Background worker for downloading chapters using API (sequential)"""
    
    # Signals
    progress = pyqtSignal(int, int, str)  # current, total, message
    chapterComplete = pyqtSignal(str, bool)  # chapter_number, success
    finished = pyqtSignal(int, int)  # success_count, total_count
    error = pyqtSignal(str)
    
    def __init__(self, series: Series, chapters: list[Book], parent=None):
        super().__init__(parent)
        self.series = series
        self.chapters = chapters
        self._stop_requested = False
    
    def run(self):
        """Run the download in background thread (sequential with browser restart per chapter)"""
        config = get_config()
        success_count = 0
        
        try:
            # Create download directory
            download_dir = Path(config.download_directory)
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Create downloader
            downloader = APIChapterDownloader(
                download_dir=download_dir,
                max_concurrent_images=config.max_concurrent_images,
                max_retries=config.max_retries
            )
            
            results = []
            
            # Process chapters sequentially with fresh browser per chapter
            for idx, book in enumerate(self.chapters):
                if self._stop_requested:
                    break
                
                self.progress.emit(idx, len(self.chapters), f"Loading Chapter {book.chapter_no}...")
                
                # Create chapter directory
                safe_title = downloader.sanitize_filename(self.series.title, max_length=50)
                safe_chapter = downloader.sanitize_filename(f"Chapter_{book.chapter_no}_{book.title}", max_length=80)
                chapter_dir = download_dir / safe_title / safe_chapter
                chapter_dir.mkdir(parents=True, exist_ok=True)
                
                # Initialize fresh browser for each chapter
                browser = None
                try:
                    browser = BrowserManager()
                    browser.init_browser(headless=config.headless_mode, enable_network_logs=True)
                    driver = browser.get_driver()
                    
                    # Navigate to reader page
                    reader_url = get_reader_url(self.series.series_id, book.book_id)
                    driver.get(reader_url)
                    
                    # Wait for images to load
                    time.sleep(config.image_load_delay)
                    
                    # Get network logs to extract image URLs
                    logs = driver.get_log("performance")
                    image_urls = set()
                    
                    for entry in logs:
                        try:
                            log = json.loads(entry["message"])["message"]
                            if log["method"] == "Network.requestWillBeSent":
                                url = log["params"]["request"]["url"]
                                if "akari.kagane.org/api/v2/books/file/" in url:
                                    image_urls.add(url)
                        except (json.JSONDecodeError, KeyError):
                            continue
                    
                    image_urls = list(image_urls)
                    
                    if not image_urls:
                        results.append((book, False, chapter_dir, 0))
                        self.chapterComplete.emit(book.chapter_no, False)
                        continue
                    
                    self.progress.emit(idx, len(self.chapters), f"Ch.{book.chapter_no}: Downloading {len(image_urls)} images...")
                    
                    # Download images
                    pages_downloaded = downloader.download_from_urls(image_urls, chapter_dir)
                    
                    success = pages_downloaded > 0
                    results.append((book, success, chapter_dir, pages_downloaded))
                    self.chapterComplete.emit(book.chapter_no, success)
                    
                except Exception as e:
                    results.append((book, False, chapter_dir, 0))
                    self.chapterComplete.emit(book.chapter_no, False)
                
                finally:
                    # Close browser after each chapter to clear network logs
                    if browser:
                        try:
                            browser.close_browser()
                        except:
                            pass
            
            # Convert files if needed
            if config.download_format in ("pdf", "cbz") and not self._stop_requested:
                self.progress.emit(len(self.chapters), len(self.chapters), f"Converting to {config.download_format.upper()}...")
                for book, success, chapter_dir, _ in results:
                    if self._stop_requested:
                        break
                    if success and chapter_dir and chapter_dir.exists():
                        try:
                            if config.download_format == "pdf":
                                create_pdf(chapter_dir, delete_images=not config.keep_images)
                            elif config.download_format == "cbz":
                                create_cbz(chapter_dir, series=self.series, book=book, delete_images=not config.keep_images)
                        except Exception:
                            pass  # Conversion error, continue
            
            # Count successes
            for _, success, _, _ in results:
                if success:
                    success_count += 1
            
            downloader.close()
            
            self.finished.emit(success_count, len(self.chapters))
            
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        """Request stop"""
        self._stop_requested = True
        self.terminate()

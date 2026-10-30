"""
Download Worker - Background thread for downloading chapters using API
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

# Add parent directory to path to import src modules
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import get_config
from src.scraper import Series, Book
from src.scraper.api_downloader import APIChapterDownloader
from src.converter import create_pdf, create_cbz


class DownloadWorker(QThread):
    """Background worker for downloading chapters using API (sequential)"""
    
    # Signals
    progress = pyqtSignal(float, int, str)  # current, total, message
    chapterComplete = pyqtSignal(str, bool)  # chapter_number, success
    finished = pyqtSignal(int, int)  # success_count, total_count
    error = pyqtSignal(str)
    
    def __init__(self, series: Series, chapters: list[Book], parent=None):
        super().__init__(parent)
        self.series = series
        self.chapters = chapters
        self._stop_requested = False
    
    def run(self):
        """Run the download in background thread using the API directly"""
        config = get_config()
        success_count = 0
        downloader = None
        
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
            
            # Process chapters sequentially
            for idx, book in enumerate(self.chapters):
                if self._stop_requested:
                    break
                
                self.progress.emit(idx, len(self.chapters), f"Loading Chapter {book.chapter_no}...")
                
                # Create chapter directory
                safe_title = downloader.sanitize_filename(self.series.title, max_length=50)
                safe_chapter = downloader.sanitize_filename(f"Chapter_{book.chapter_no}_{book.title}", max_length=80)
                chapter_dir = download_dir / safe_title / safe_chapter
                chapter_dir.mkdir(parents=True, exist_ok=True)
                
                try:
                    image_urls = downloader.get_page_urls(book.book_id)
                    if not image_urls:
                        results.append((book, False, chapter_dir, 0))
                        self.chapterComplete.emit(book.chapter_no, False)
                        self.progress.emit(idx + 1, len(self.chapters), f"Chapter {book.chapter_no} failed")
                        continue
                    
                    self.progress.emit(idx, len(self.chapters), f"Ch.{book.chapter_no}: Downloading {len(image_urls)} images...")
                    
                    def on_image_progress(done: int, total: int, chapter_no: str = book.chapter_no):
                        self.progress.emit(
                            idx + done / max(total, 1),
                            len(self.chapters),
                            f"Ch.{chapter_no}: {done}/{total} images..."
                        )
                    
                    # Download images
                    pages_downloaded = downloader.download_from_urls(image_urls, chapter_dir, on_image_progress)
                    
                    success = pages_downloaded > 0
                    results.append((book, success, chapter_dir, pages_downloaded))
                    self.chapterComplete.emit(book.chapter_no, success)
                    self.progress.emit(idx + 1, len(self.chapters), f"Chapter {book.chapter_no} complete")
                    
                except Exception:
                    results.append((book, False, chapter_dir, 0))
                    self.chapterComplete.emit(book.chapter_no, False)
                    self.progress.emit(idx + 1, len(self.chapters), f"Chapter {book.chapter_no} failed")
            
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
            
            self.finished.emit(success_count, len(self.chapters))
            
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if downloader:
                downloader.close()
    
    def stop(self):
        """Request stop"""
        self._stop_requested = True
        self.terminate()

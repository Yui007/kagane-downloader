"""
Download Worker - Background thread for downloading chapters
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import get_config
from src.scraper import BrowserManager, ChapterDownloader, MangaInfo, Chapter
from src.converter import create_pdf, create_cbz


class DownloadWorker(QThread):
    """Background worker for downloading chapters"""
    
    # Signals
    progress = pyqtSignal(int, int, str)  # current, total, message
    chapterComplete = pyqtSignal(str, bool)  # chapter_number, success
    finished = pyqtSignal(int, int)  # success_count, total_count
    error = pyqtSignal(str)
    
    def __init__(self, manga: MangaInfo, chapters: list, parent=None):
        super().__init__(parent)
        self.manga = manga
        self.chapters = chapters
        self._browser = None
        self._stop_requested = False
    
    def run(self):
        """Run the download in background thread"""
        config = get_config()
        success_count = 0
        
        try:
            self.progress.emit(0, len(self.chapters), "Initializing browser...")
            self._browser = BrowserManager()
            self._browser.init_browser()
            
            download_dir = Path(config.download_directory)
            download_dir.mkdir(parents=True, exist_ok=True)
            
            downloader = ChapterDownloader(
                self._browser,
                download_dir,
                config.image_load_delay,
                max_concurrent_chapters=config.max_concurrent_chapters,
                max_concurrent_images=config.max_concurrent_images,
                max_retries=config.max_retries
            )
            
            # Define progress callback
            def on_progress(current, total, msg):
                if not self._stop_requested:
                    self.progress.emit(current, total, msg)
            
            # Download chapters concurrently
            results = downloader.download_chapters_concurrent(
                self.chapters,
                self.manga.title,
                progress_callback=on_progress
            )
            
            # Convert files if needed
            if config.download_format in ("pdf", "cbz"):
                self.progress.emit(len(self.chapters), len(self.chapters), f"Converting to {config.download_format.upper()}...")
                for chapter, success, chapter_dir in results:
                    if self._stop_requested:
                        break
                    if success and chapter_dir and chapter_dir.exists():
                        try:
                            if config.download_format == "pdf":
                                create_pdf(chapter_dir, delete_images=not config.keep_images)
                            elif config.download_format == "cbz":
                                create_cbz(chapter_dir, manga=self.manga, chapter=chapter, delete_images=not config.keep_images)
                        except Exception as e:
                            pass  # Conversion error, continue
            
            # Emit results
            for chapter, success, chapter_dir in results:
                if success:
                    success_count += 1
                self.chapterComplete.emit(chapter.number, success)
            
            self.progress.emit(len(self.chapters), len(self.chapters), "Closing browser...")
            self._browser.close_browser()
            self._browser = None
            
            self.finished.emit(success_count, len(self.chapters))
            
        except Exception as e:
            if self._browser:
                try:
                    self._browser.close_browser()
                except:
                    pass
            self.error.emit(str(e))
    
    def stop(self):
        """Request stop and close browser"""
        self._stop_requested = True
        if self._browser:
            try:
                self._browser.close_browser()
            except:
                pass
        self.terminate()

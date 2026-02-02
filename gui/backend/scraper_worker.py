"""
Scraper Worker - Background thread for manga scraping
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, QObject

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scraper import BrowserManager, MangaScraper, MangaInfo
from config import get_config


class ScraperWorker(QThread):
    """Background worker for scraping manga info"""
    
    # Signals
    finished = pyqtSignal(object)  # MangaInfo
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self._browser = None
    
    def run(self):
        """Run the scraping in background thread"""
        try:
            self.progress.emit("Initializing browser...")
            self._browser = BrowserManager()
            config = get_config()
            self._browser.init_browser(headless=config.headless_mode)
            
            self.progress.emit("Loading manga page...")
            scraper = MangaScraper(self._browser)
            manga = scraper.scrape_manga(self.url)
            
            self.progress.emit("Closing browser...")
            self._browser.close_browser()
            self._browser = None
            
            if manga.title:
                self.finished.emit(manga)
            else:
                self.error.emit("Failed to load manga information")
                
        except Exception as e:
            if self._browser:
                try:
                    self._browser.close_browser()
                except:
                    pass
            self.error.emit(str(e))
    
    def stop(self):
        """Stop the worker and close browser"""
        if self._browser:
            try:
                self._browser.close_browser()
            except:
                pass
        self.terminate()

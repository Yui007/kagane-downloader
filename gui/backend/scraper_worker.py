"""
Scraper Worker - Background thread for manga scraping using API
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, QObject

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scraper import KaganeScraper, Series
from config import get_config


class ScraperWorker(QThread):
    """Background worker for scraping manga info using API"""
    
    # Signals
    finished = pyqtSignal(object)  # Series
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self._scraper = None
    
    def run(self):
        """Run the scraping in background thread using API"""
        try:
            self.progress.emit("Connecting to API...")
            self._scraper = KaganeScraper()
            
            self.progress.emit("Fetching series information...")
            series = self._scraper.get_series(self.url)
            
            if series.title:
                self.finished.emit(series)
            else:
                self.error.emit("Failed to load series information")
                
        except ValueError as e:
            self.error.emit(f"Invalid URL: {e}")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if self._scraper:
                try:
                    self._scraper.close()
                except:
                    pass
    
    def stop(self):
        """Stop the worker"""
        if self._scraper:
            try:
                self._scraper.close()
            except:
                pass
        self.terminate()

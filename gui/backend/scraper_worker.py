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
                # Download cover image as base64 to bypass Cloudflare in GUI
                series.local_cover = series.cover_url
                if series.cover_url:
                    try:
                        self.progress.emit("Downloading cover image...")
                        from curl_cffi import requests
                        import base64
                        response = requests.get(series.cover_url, impersonate="chrome110", timeout=10)
                        if response.status_code == 200:
                            content_type = response.headers.get("content-type", "image/jpeg")
                            b64_data = base64.b64encode(response.content).decode("utf-8")
                            series.local_cover = f"data:{content_type};base64,{b64_data}"
                    except Exception:
                        pass
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

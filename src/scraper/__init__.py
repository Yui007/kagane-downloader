"""
Scraper Package - Browser automation and manga/chapter extraction
"""

from .models import MangaInfo, Chapter
from .browser import BrowserManager
from .manga import MangaScraper
from .downloader import ChapterDownloader

__all__ = ["MangaInfo", "Chapter", "BrowserManager", "MangaScraper", "ChapterDownloader"]

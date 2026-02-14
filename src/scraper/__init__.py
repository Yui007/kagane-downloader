"""
Scraper Package - API client and manga/chapter extraction

New API-based approach (recommended):
- KaganeScraper: High-level API scraper
- KaganeAPIClient: Low-level API client
- Series, Book, etc.: Data models from API
- APIChapterDownloader: Downloads images from captured URLs

Legacy browser-based approach (deprecated):
- MangaScraper: Selenium-based scraper
- ChapterDownloader: Selenium-based downloader
- BrowserManager: Browser automation
"""

# New API-based modules (recommended)
from .api_client import KaganeAPIClient, APIConfig
from .api_models import (
    Series, Book, Genre, Tag, AlternateTitle,
    Group, Uploader, SeriesCover, SeriesLink, SeriesStaff,
    parse_series, get_image_url, IMAGE_BASE_URL
)
from .api_scraper import KaganeScraper, fetch_series
from .api_downloader import APIChapterDownloader, get_image_urls_from_browser, get_reader_url

# # Legacy modules (deprecated - kept for backward compatibility)
# from .models import MangaInfo, Chapter
from .browser import BrowserManager
# from .manga import MangaScraper
# from .downloader import ChapterDownloader

__all__ = [
    # New API-based (recommended)
    "KaganeAPIClient",
    "APIConfig", 
    "Series",
    "Book",
    "Genre",
    "Tag",
    "AlternateTitle",
    "Group",
    "Uploader",
    "SeriesCover",
    "SeriesLink",
    "SeriesStaff",
    "parse_series",
    "get_image_url",
    "IMAGE_BASE_URL",
    "KaganeScraper",
    "fetch_series",
    "APIChapterDownloader",
    "get_image_urls_from_browser",
    "get_reader_url",
    # Legacy (deprecated)
    # "MangaInfo",
    # "Chapter",
    "BrowserManager",
    # "MangaScraper",
    # "ChapterDownloader",
]

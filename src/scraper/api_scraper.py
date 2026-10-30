"""
High-level Kagane API Scraper
Provides easy-to-use interface for fetching manga data
"""

import re
from typing import Optional

from .api_client import KaganeAPIClient, APIConfig
from .api_models import Series, Book, parse_series, parse_books


class KaganeScraper:
    """High-level scraper for Kagane using the API"""
    
    # URLs like: https://kagane.moe/series/omni-class-unlimited-awakening-019c2b2c-eaa0-7f30-ba25-61a2e4c4df0f
    SERIES_URL_PATTERN = re.compile(
        r'(?:https?://)?(?:www\.)?kagane\.(?:to|moe|net|cx)/series/([^/?#]+)',
        re.IGNORECASE
    )
    
    # Series IDs are the trailing UUID of the URL slug
    SERIES_ID_PATTERN = re.compile(
        r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}',
        re.IGNORECASE
    )
    
    def __init__(self, config: Optional[APIConfig] = None):
        self.client = KaganeAPIClient(config)
    
    @classmethod
    def extract_series_id(cls, url: str) -> Optional[str]:
        """Extract series ID from a Kagane URL or ID"""
        match = cls.SERIES_URL_PATTERN.search(url)
        candidate = match.group(1) if match else url.strip()
        
        id_match = cls.SERIES_ID_PATTERN.search(candidate)
        return id_match.group(0) if id_match else None
    
    def get_series(self, url_or_id: str) -> Series:
        """
        Fetch series data from URL or ID.
        
        Args:
            url_or_id: Either a full URL like https://kagane.moe/series/xxx
                      or just the series ID (UUID)
        
        Returns:
            Series object with all metadata and books
        """
        series_id = self.extract_series_id(url_or_id)
        if not series_id:
            raise ValueError(f"Invalid series URL or ID: {url_or_id}")
        
        data = self.client.get_series(series_id)
        series = parse_series(data)
        series.series_books = parse_books(self.client.get_books(series_id))
        return series
    
    def get_books(self, url_or_id: str) -> list[Book]:
        """
        Fetch just the books/chapters for a series.
        
        Args:
            url_or_id: Series URL or ID
        
        Returns:
            List of Book objects
        """
        series = self.get_series(url_or_id)
        return series.series_books
    
    def close(self):
        """Close the API client"""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience function for quick access
def fetch_series(url_or_id: str) -> Series:
    """
    Quick function to fetch series data.
    
    Args:
        url_or_id: Series URL or ID
    
    Returns:
        Series object
    """
    with KaganeScraper() as scraper:
        return scraper.get_series(url_or_id)

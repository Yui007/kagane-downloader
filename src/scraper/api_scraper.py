"""
High-level Kagane API Scraper
Provides easy-to-use interface for fetching manga data
"""

import re
from typing import Optional

from .api_client import KaganeAPIClient, APIConfig
from .api_models import Series, Book, parse_series


class KaganeScraper:
    """High-level scraper for Kagane using the API"""
    
    # Pattern to extract series ID from URL
    # URLs like: https://kagane.org/series/019c2071-7760-7481-acf2-35d57d2912a9
    SERIES_URL_PATTERN = re.compile(
        r'(?:https?://)?(?:www\.)?kagane\.org/series/([a-f0-9-]+)',
        re.IGNORECASE
    )
    
    def __init__(self, config: Optional[APIConfig] = None):
        self.client = KaganeAPIClient(config)
    
    @classmethod
    def extract_series_id(cls, url: str) -> Optional[str]:
        """Extract series ID from a Kagane URL"""
        match = cls.SERIES_URL_PATTERN.search(url)
        if match:
            return match.group(1)
        
        # If it's already just a UUID, return it
        uuid_pattern = re.compile(
            r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
            re.IGNORECASE
        )
        if uuid_pattern.match(url.strip()):
            return url.strip()
        
        return None
    
    def get_series(self, url_or_id: str) -> Series:
        """
        Fetch series data from URL or ID.
        
        Args:
            url_or_id: Either a full URL like https://kagane.org/series/xxx
                      or just the series ID (UUID)
        
        Returns:
            Series object with all metadata and books
        """
        series_id = self.extract_series_id(url_or_id)
        if not series_id:
            raise ValueError(f"Invalid series URL or ID: {url_or_id}")
        
        data = self.client.get_series(series_id)
        return parse_series(data)
    
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

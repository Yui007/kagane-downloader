"""
Kagane API Client
Handles all HTTP communication with the Kagane API
"""

from curl_cffi import requests
from typing import Optional, Any
from dataclasses import dataclass


@dataclass
class APIConfig:
    """Configuration for the Kagane API"""
    base_url: str = "https://kagane.moe/api/v2"
    timeout: int = 30
    max_retries: int = 3


class KaganeAPIClient:
    """Low-level API client for Kagane"""
    
    def __init__(self, config: Optional[APIConfig] = None):
        self.config = config or APIConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "KaganeDownloader/2.0"
        })
    
    def _make_request(self, endpoint: str) -> dict:
        """Make a GET request to the API"""
        url = f"{self.config.base_url}/{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(url, timeout=self.config.timeout, impersonate="chrome110")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise
                continue
        
        return {}
    
    def get_series(self, series_id: str) -> dict:
        """Get series information by ID"""
        return self._make_request(f"series/{series_id}")
    
    def get_books(self, series_id: str) -> dict:
        """Get the packed chapter list for a series"""
        return self._make_request(f"series/{series_id}/books/index?fields=List")
    
    def get_page_urls(self, book_id: str) -> list[str]:
        """Get ordered page image URLs for a chapter"""
        origin = self.config.base_url.replace("/api/v2", "")
        
        integrity = self.session.post(
            f"{origin}/api/integrity",
            timeout=self.config.timeout,
            impersonate="chrome"
        )
        integrity.raise_for_status()
        token = integrity.json()["token"]
        
        response = self.session.post(
            f"{self.config.base_url}/books/{book_id}?intent=Read",
            headers={
                "Content-Type": "application/json",
                "X-Integrity-Token": token
            },
            data="{}",
            timeout=self.config.timeout,
            impersonate="chrome"
        )
        response.raise_for_status()
        data = response.json()
        
        cache_url = data.get("cache_url") or "https://kstatic.to"
        access_token = data["access_token"]
        pages = sorted(data["manifest"]["pages"], key=lambda page: page["page_no"])
        return [
            f"{cache_url}/api/v2/books/page/{book_id}/{page['page_id']}.{page['ext']}?token={access_token}"
            for page in pages
        ]
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

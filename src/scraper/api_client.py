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
    base_url: str = "https://yuzuki.kagane.org/api/v2"
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
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

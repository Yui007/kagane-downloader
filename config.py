"""
Configuration management for Kagane Downloader
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal


CONFIG_FILE = Path("config.json")


@dataclass
class Config:
    """Application configuration settings"""
    
    # Download format: images, pdf, cbz
    download_format: Literal["images", "pdf", "cbz"] = "images"
    
    # Keep original images after PDF/CBZ conversion
    keep_images: bool = False
    
    # Max concurrent chapter downloads (using browser tabs)
    max_concurrent_chapters: int = 3
    
    # Max concurrent image downloads per chapter
    max_concurrent_images: int = 5
    
    # Max chapters to display (0 = show all)
    max_display_chapters: int = 0
    
    # Download directory path
    download_directory: str = "downloads"
    
    # Enable/disable logging
    enable_logs: bool = False
    
    # Delay for chapter images to load (seconds)
    image_load_delay: int = 15
    
    # Max retries for failed image downloads
    max_retries: int = 3
    
    def save(self) -> None:
        """Save configuration to file"""
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file, or create default if not exists"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**data)
            except (json.JSONDecodeError, TypeError):
                # Return default config if file is corrupted
                return cls()
        return cls()


def get_config() -> Config:
    """Get the current configuration"""
    return Config.load()


def save_config(config: Config) -> None:
    """Save the configuration"""
    config.save()

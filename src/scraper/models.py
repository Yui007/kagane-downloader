"""
Data models for manga and chapter information
"""

from dataclasses import dataclass, field


@dataclass
class Chapter:
    """Represents a manga chapter"""
    id: str = ""
    number: str = ""
    title: str = ""
    url: str = ""
    date: str = ""
    pages: str = ""
    views: str = ""


@dataclass
class MangaInfo:
    """Represents manga information"""
    title: str = ""
    alt_titles: list = field(default_factory=list)
    cover_url: str = ""
    author: str = ""
    description: str = ""
    source: str = ""
    is_erotica: bool = False
    status: str = ""
    total_chapters: str = ""
    views: str = ""
    genres: list = field(default_factory=list)
    chapters: list = field(default_factory=list)

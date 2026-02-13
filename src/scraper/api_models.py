"""
Data models for Kagane API responses
Maps API JSON responses to Python dataclasses
"""

from dataclasses import dataclass, field
from typing import Optional


# Base URL for images
IMAGE_BASE_URL = "https://yuzuki.kagane.org/api/v2/image"


def get_image_url(image_id: str) -> str:
    """Generate image URL from image ID"""
    return f"{IMAGE_BASE_URL}/{image_id}"


@dataclass
class Genre:
    """Genre from API response"""
    genre_id: str = ""
    genre_name: str = ""
    is_spoiler: bool = False


@dataclass
class Tag:
    """Tag from API response"""
    tag_id: str = ""
    tag_name: str = ""
    is_spoiler: bool = False


@dataclass
class AlternateTitle:
    """Alternate title from API response"""
    label: str = ""
    title: str = ""


@dataclass
class Group:
    """Scanlation group from API response"""
    group_id: str = ""
    title: str = ""
    avatar_image_id: str = ""


@dataclass
class Uploader:
    """Uploader info from API response"""
    user_id: str = ""
    username: str = ""
    avatar_image_id: str = ""
    user_class: str = ""  # 'class' is reserved in Python


@dataclass
class Book:
    """Book/Chapter from API response"""
    book_id: str = ""
    chapter_no: str = ""
    title: str = ""
    sort_no: float = 0.0
    page_count: int = 0
    views: int = 0
    created_at: str = ""
    updated_at: str = ""
    volume_no: Optional[str] = None
    published_on: Optional[str] = None
    internal_release: bool = False
    optional_data: Optional[dict] = None
    groups: list[Group] = field(default_factory=list)
    uploader: Optional[Uploader] = None


@dataclass
class SeriesCover:
    """Series cover from API response"""
    cover_id: str = ""
    image_id: str = ""
    chapter_number: str = ""
    volume_number: Optional[str] = None
    language: str = ""
    note: Optional[str] = None
    
    @property
    def url(self) -> str:
        """Get the cover image URL"""
        if self.image_id:
            return get_image_url(self.image_id)
        return ""


@dataclass
class SeriesLink:
    """External link from API response"""
    label: str = ""
    url: str = ""


@dataclass
class SeriesStaff:
    """Staff member from API response"""
    staff_id: str = ""
    name: str = ""
    role: str = ""


@dataclass
class Series:
    """Complete series data from API response"""
    series_id: str = ""
    title: str = ""
    description: str = ""
    format: str = ""  # Manhwa, Manga, etc.
    content_rating: str = ""  # Safe, Erotica, etc.
    publication_status: str = ""  # Ongoing, Hiatus, Ended
    upload_status: str = ""
    original_language: str = ""
    translated_language: str = ""
    title_language: str = ""
    
    # Counts
    current_books: int = 0
    total_views: int = 0
    
    # Timestamps
    created_at: str = ""
    updated_at: str = ""
    
    # Optional fields
    source_id: str = ""
    tracker_id: str = ""
    average_rating: Optional[float] = None
    bayesian_rating: Optional[float] = None
    total_ratings: Optional[int] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    current_volumes: Optional[int] = None
    total_volumes: Optional[int] = None
    total_books: Optional[int] = None
    edition_info: Optional[str] = None
    distribution: Optional[str] = None
    
    # Lists
    genres: list[Genre] = field(default_factory=list)
    tags: list[Tag] = field(default_factory=list)
    series_alternate_titles: list[AlternateTitle] = field(default_factory=list)
    series_books: list[Book] = field(default_factory=list)
    series_covers: list[SeriesCover] = field(default_factory=list)
    series_links: list[SeriesLink] = field(default_factory=list)
    series_staff: list[SeriesStaff] = field(default_factory=list)
    
    @property
    def cover_url(self) -> str:
        """Get the cover image URL from the first cover"""
        if self.series_covers and self.series_covers[0].image_id:
            return self.series_covers[0].url
        return ""


# Parser functions to convert API JSON to dataclasses

def parse_genre(data: dict) -> Genre:
    return Genre(
        genre_id=data.get("genre_id", ""),
        genre_name=data.get("genre_name", ""),
        is_spoiler=data.get("is_spoiler", False)
    )


def parse_tag(data: dict) -> Tag:
    return Tag(
        tag_id=data.get("tag_id", ""),
        tag_name=data.get("tag_name", ""),
        is_spoiler=data.get("is_spoiler", False)
    )


def parse_alternate_title(data: dict) -> AlternateTitle:
    return AlternateTitle(
        label=data.get("label", ""),
        title=data.get("title", "")
    )


def parse_group(data: dict) -> Group:
    return Group(
        group_id=data.get("group_id", ""),
        title=data.get("title", ""),
        avatar_image_id=data.get("avatar_image_id", "")
    )


def parse_uploader(data: dict) -> Uploader:
    return Uploader(
        user_id=data.get("user_id", ""),
        username=data.get("username", ""),
        avatar_image_id=data.get("avatar_image_id", ""),
        user_class=data.get("class", "")
    )


def parse_book(data: dict) -> Book:
    groups = [parse_group(g) for g in data.get("groups", [])]
    uploader = parse_uploader(data["uploader"]) if data.get("uploader") else None
    
    return Book(
        book_id=data.get("book_id", ""),
        chapter_no=data.get("chapter_no", ""),
        title=data.get("title", ""),
        sort_no=data.get("sort_no", 0.0),
        page_count=data.get("page_count", 0),
        views=data.get("views", 0),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        volume_no=data.get("volume_no"),
        published_on=data.get("published_on"),
        internal_release=data.get("internal_release", False),
        optional_data=data.get("optional_data"),
        groups=groups,
        uploader=uploader
    )


def parse_series_cover(data: dict) -> SeriesCover:
    return SeriesCover(
        cover_id=data.get("cover_id", ""),
        image_id=data.get("image_id", ""),
        chapter_number=data.get("chapter_number", ""),
        volume_number=data.get("volume_number"),
        language=data.get("language", ""),
        note=data.get("note")
    )


def parse_series_link(data: dict) -> SeriesLink:
    return SeriesLink(
        label=data.get("label", ""),
        url=data.get("url", "")
    )


def parse_series_staff(data: dict) -> SeriesStaff:
    return SeriesStaff(
        staff_id=data.get("staff_id", ""),
        name=data.get("name", ""),
        role=data.get("role", "")
    )


def parse_series(data: dict) -> Series:
    """Parse complete series data from API response"""
    genres = [parse_genre(g) for g in data.get("genres", [])]
    tags = [parse_tag(t) for t in data.get("tags", [])]
    alt_titles = [parse_alternate_title(t) for t in data.get("series_alternate_titles", [])]
    books = [parse_book(b) for b in data.get("series_books", [])]
    covers = [parse_series_cover(c) for c in data.get("series_covers", [])]
    links = [parse_series_link(l) for l in data.get("series_links", [])]
    staff = [parse_series_staff(s) for s in data.get("series_staff", [])]
    
    return Series(
        series_id=data.get("series_id", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        format=data.get("format", ""),
        content_rating=data.get("content_rating", ""),
        publication_status=data.get("publication_status", ""),
        upload_status=data.get("upload_status", ""),
        original_language=data.get("original_language", ""),
        translated_language=data.get("translated_language", ""),
        title_language=data.get("title_language", ""),
        current_books=data.get("current_books", 0),
        total_views=data.get("total_views", 0),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        source_id=data.get("source_id", ""),
        tracker_id=data.get("tracker_id", ""),
        average_rating=data.get("average_rating"),
        bayesian_rating=data.get("bayesian_rating"),
        total_ratings=data.get("total_ratings"),
        start_year=data.get("start_year"),
        end_year=data.get("end_year"),
        current_volumes=data.get("current_volumes"),
        total_volumes=data.get("total_volumes"),
        total_books=data.get("total_books"),
        edition_info=data.get("edition_info"),
        distribution=data.get("distribution"),
        genres=genres,
        tags=tags,
        series_alternate_titles=alt_titles,
        series_books=books,
        series_covers=covers,
        series_links=links,
        series_staff=staff
    )

"""
CBZ archive creation with ComicInfo.xml metadata
"""

import zipfile
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

from src.scraper.models import MangaInfo, Chapter


def generate_comic_info(
    manga: MangaInfo,
    chapter: Chapter,
    page_count: int
) -> str:
    """
    Generate ComicInfo.xml content for a chapter.
    
    Args:
        manga: Manga information
        chapter: Chapter information
        page_count: Number of pages in the chapter
        
    Returns:
        XML string for ComicInfo.xml
    """
    root = ET.Element("ComicInfo")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")
    
    # Title
    ET.SubElement(root, "Title").text = chapter.title or f"Chapter {chapter.number}"
    
    # Series
    ET.SubElement(root, "Series").text = manga.title
    
    # Number (chapter number)
    if chapter.number:
        ET.SubElement(root, "Number").text = chapter.number
    
    # Writer/Author
    if manga.author:
        ET.SubElement(root, "Writer").text = manga.author
    
    # Summary/Description
    if manga.description:
        ET.SubElement(root, "Summary").text = manga.description
    
    # Genre
    if manga.genres:
        ET.SubElement(root, "Genre").text = ", ".join(manga.genres)
    
    # Page count
    ET.SubElement(root, "PageCount").text = str(page_count)
    
    # Web (source URL)
    if chapter.url:
        ET.SubElement(root, "Web").text = chapter.url
    
    # Manga reading direction
    ET.SubElement(root, "Manga").text = "Yes"
    
    # Status
    if manga.status:
        status_map = {
            "ONGOING": "Ongoing",
            "COMPLETED": "Ended",
            "HIATUS": "Hiatus"
        }
        ET.SubElement(root, "Series.Status").text = status_map.get(manga.status.upper(), manga.status)
    
    # AgeRating for erotica
    if manga.is_erotica:
        ET.SubElement(root, "AgeRating").text = "Adults Only 18+"
    
    # Generate XML string with declaration
    xml_str = '<?xml version="1.0" encoding="utf-8"?>\n'
    xml_str += ET.tostring(root, encoding='unicode')
    
    return xml_str


def create_cbz(
    image_dir: Path,
    output_path: Optional[Path] = None,
    manga: Optional[MangaInfo] = None,
    chapter: Optional[Chapter] = None,
    delete_images: bool = False
) -> Path:
    """
    Create a CBZ archive from images in a directory.
    
    Args:
        image_dir: Directory containing images
        output_path: Path for the output CBZ (default: same dir with .cbz extension)
        manga: Optional MangaInfo for ComicInfo.xml generation
        chapter: Optional Chapter for ComicInfo.xml generation
        delete_images: Whether to delete source images after CBZ creation
        
    Returns:
        Path to the created CBZ file
    """
    if output_path is None:
        output_path = image_dir.parent / f"{image_dir.name}.cbz"
    
    # Get all image files sorted
    image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    images = sorted(
        [f for f in image_dir.iterdir() if f.is_file() and f.suffix.lower() in image_extensions],
        key=lambda p: p.stem
    )
    
    if not images:
        raise ValueError(f"No images found in {image_dir}")
    
    # Create CBZ (which is just a zip file)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as cbz:
        # Add ComicInfo.xml if we have manga/chapter info
        if manga and chapter:
            comic_info = generate_comic_info(manga, chapter, len(images))
            cbz.writestr("ComicInfo.xml", comic_info.encode('utf-8'))
        
        # Add images
        for img_path in images:
            # Add with just the filename (flat structure)
            cbz.write(img_path, img_path.name)
    
    # Delete original images if requested
    if delete_images:
        for img_path in images:
            try:
                img_path.unlink()
            except Exception:
                pass
        
        # Try to remove the directory if empty
        try:
            image_dir.rmdir()
        except Exception:
            pass
    
    return output_path

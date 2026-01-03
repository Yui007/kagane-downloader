"""
Chapter image downloader with blob URL extraction
Supports concurrent chapter downloads using browser tabs
"""

import re
import time
import base64
from pathlib import Path
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .models import Chapter, MangaInfo
from .browser import BrowserManager


class ChapterDownloader:
    """Downloads chapter images using JavaScript blob extraction with concurrent tab support"""
    
    def __init__(
        self, 
        browser_manager: BrowserManager, 
        download_dir: Path, 
        image_load_delay: int = 15,
        max_concurrent_chapters: int = 3,
        max_retries: int = 3
    ):
        self.browser = browser_manager
        self.driver = browser_manager.get_driver()
        self.download_dir = download_dir
        self.image_load_delay = image_load_delay
        self.max_concurrent_chapters = max_concurrent_chapters
        self.max_retries = max_retries
    
    @staticmethod
    def sanitize_filename(name: str, max_length: int = 80) -> str:
        """Sanitize a string to be safe for Windows filenames"""
        sanitized = re.sub(r'[<>:"/\\|?*~\[\]{}]', '_', name)
        sanitized = re.sub(r'_+', '_', sanitized)
        sanitized = sanitized.strip(' _')
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip(' _')
        return sanitized
    
    def download_chapters_concurrent(
        self,
        chapters: list[Chapter],
        manga_title: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[tuple[Chapter, bool, Path]]:
        """
        Download multiple chapters concurrently using browser tabs.
        
        Args:
            chapters: List of chapters to download
            manga_title: Title of the manga (for folder structure)
            progress_callback: Optional callback(chapter_idx, total, status_msg)
            
        Returns:
            List of tuples (chapter, success, chapter_dir)
        """
        results = []
        total_chapters = len(chapters)
        
        # Process chapters in batches based on max_concurrent_chapters
        for batch_start in range(0, total_chapters, self.max_concurrent_chapters):
            batch_end = min(batch_start + self.max_concurrent_chapters, total_chapters)
            batch = chapters[batch_start:batch_end]
            
            # Store tab handles in order (index corresponds to batch index)
            tab_handles = []
            original_window = self.driver.current_window_handle
            
            # First, open all the tabs we need
            for i in range(len(batch) - 1):
                self.driver.switch_to.new_window('tab')
                time.sleep(0.2)
            
            # Get all current window handles
            all_handles = self.driver.window_handles
            
            # Navigate each tab to its chapter URL
            for i, chapter in enumerate(batch):
                try:
                    # Use appropriate tab handle
                    if i < len(all_handles):
                        self.driver.switch_to.window(all_handles[i])
                        self.driver.get(chapter.url)
                        tab_handles.append(all_handles[i])
                    
                    if progress_callback:
                        progress_callback(batch_start + i + 1, total_chapters, f"Opening Ch.{chapter.number}")
                        
                except Exception as e:
                    tab_handles.append(None)
            
            # Wait for all tabs to start loading
            time.sleep(2)
            
            # Wait for reader to load in each tab
            for i, chapter in enumerate(batch):
                handle = tab_handles[i] if i < len(tab_handles) else None
                if handle:
                    try:
                        self.driver.switch_to.window(handle)
                        WebDriverWait(self.driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.reader-pages-content"))
                        )
                    except TimeoutException:
                        pass  # Will handle the failure when extracting
                    except Exception:
                        pass
            
            # Wait for blob images to generate in all tabs
            if progress_callback:
                progress_callback(batch_start + len(batch), total_chapters, f"Waiting {self.image_load_delay}s for images...")
            time.sleep(self.image_load_delay)
            
            # Extract images from each tab
            for i, chapter in enumerate(batch):
                handle = tab_handles[i] if i < len(tab_handles) else None
                
                # Create chapter directory
                safe_title = self.sanitize_filename(manga_title, max_length=50)
                safe_chapter = self.sanitize_filename(f"Chapter_{chapter.number}_{chapter.title}", max_length=80)
                chapter_dir = self.download_dir / safe_title / safe_chapter
                
                if not handle:
                    results.append((chapter, False, chapter_dir))
                    continue
                
                try:
                    self.driver.switch_to.window(handle)
                    chapter_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Get expected page count from chapter metadata
                    expected_pages = int(chapter.pages) if chapter.pages and chapter.pages.isdigit() else 0
                    
                    # Get actual page count from DOM
                    page_containers = self.driver.find_elements(By.CSS_SELECTOR, "div.page-container[data-page]")
                    total_pages = len(page_containers)
                    
                    # Use the larger of expected or actual (sometimes DOM has more than listed)
                    target_pages = max(expected_pages, total_pages) if expected_pages > 0 else total_pages
                    
                    if progress_callback:
                        progress_callback(batch_start + i + 1, total_chapters, f"Extracting Ch.{chapter.number} ({target_pages} pages)")
                    
                    # Extract all images with retries
                    images_saved = self._extract_all_images_fast(chapter_dir, total_pages, None)
                    
                    # Validate page count - allow 1 page tolerance
                    min_required = max(1, expected_pages - 1) if expected_pages > 0 else 1
                    
                    # If not enough pages, try additional waits and retries
                    retry_count = 0
                    while images_saved < min_required and retry_count < self.max_retries:
                        retry_count += 1
                        # Wait a bit more for images to load
                        time.sleep(3)
                        # Re-extract
                        images_saved = self._extract_all_images_fast(chapter_dir, total_pages, None)
                        if progress_callback:
                            progress_callback(batch_start + i + 1, total_chapters, f"Retry {retry_count}: Ch.{chapter.number} ({images_saved}/{expected_pages} pages)")
                    
                    # Final validation
                    success = images_saved >= min_required
                    results.append((chapter, success, chapter_dir))
                    
                except Exception as e:
                    results.append((chapter, False, chapter_dir))
            
            # Close extra tabs (keep only the original window)
            for i, handle in enumerate(tab_handles):
                if handle and handle != original_window:
                    try:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                    except Exception:
                        pass
            
            # Switch back to original window
            try:
                self.driver.switch_to.window(original_window)
            except Exception:
                # If original window is closed, use first available
                if self.driver.window_handles:
                    self.driver.switch_to.window(self.driver.window_handles[0])
        
        return results
    
    def download_chapter(
        self, 
        chapter: Chapter, 
        manga_title: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> tuple[bool, Path]:
        """
        Download a single chapter.
        
        Args:
            chapter: The chapter to download
            manga_title: Title of the manga (for folder structure)
            progress_callback: Optional callback(current, total) for progress updates
            
        Returns:
            Tuple of (success, chapter_directory_path)
        """
        
        # Sanitize folder names
        safe_title = self.sanitize_filename(manga_title, max_length=50)
        safe_chapter = self.sanitize_filename(f"Chapter_{chapter.number}_{chapter.title}", max_length=80)
        
        chapter_dir = self.download_dir / safe_title / safe_chapter
        chapter_dir.mkdir(parents=True, exist_ok=True)
        
        # Navigate to chapter reader
        self.driver.get(chapter.url)
        
        # Wait for reader to load
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.reader-pages-content"))
            )
        except TimeoutException:
            return False, chapter_dir
        
        # Wait for all blob images to be generated
        time.sleep(self.image_load_delay)
        
        # Get total page count
        page_containers = self.driver.find_elements(By.CSS_SELECTOR, "div.page-container[data-page]")
        total_pages = len(page_containers)
        
        # Extract all images at once using JavaScript
        images_saved = self._extract_all_images_fast(chapter_dir, total_pages, progress_callback)
        
        return images_saved > 0, chapter_dir
    
    def _extract_all_images_fast(
        self, 
        chapter_dir: Path, 
        total_pages: int,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> int:
        """Extract all images at once using JavaScript - NO SCROLLING - with retry for failed images"""
        
        # JavaScript to extract specific pages (or all if no specific pages provided)
        def get_extraction_script(specific_pages: list[int] | None = None):
            if specific_pages:
                pages_js = str(specific_pages)
                return f"""
                const targetPages = {pages_js};
                const containers = document.querySelectorAll('div.page-container[data-page]');
                const results = [];
                
                for (const container of containers) {{
                    const pageNum = parseInt(container.getAttribute('data-page'));
                    if (!targetPages.includes(pageNum)) continue;
                    
                    const img = container.querySelector('img');
                    
                    if (img && img.src) {{
                        try {{
                            const canvas = document.createElement('canvas');
                            canvas.width = img.naturalWidth || img.width;
                            canvas.height = img.naturalHeight || img.height;
                            const ctx = canvas.getContext('2d');
                            ctx.drawImage(img, 0, 0);
                            const dataUrl = canvas.toDataURL('image/png');
                            results.push({{
                                page: pageNum,
                                data: dataUrl
                            }});
                        }} catch (e) {{
                            results.push({{
                                page: pageNum,
                                data: null,
                                error: e.message
                            }});
                        }}
                    }}
                }}
                
                return results;
                """
            else:
                return """
                const containers = document.querySelectorAll('div.page-container[data-page]');
                const results = [];
                
                for (const container of containers) {
                    const pageNum = container.getAttribute('data-page');
                    const img = container.querySelector('img');
                    
                    if (img && img.src) {
                        try {
                            const canvas = document.createElement('canvas');
                            canvas.width = img.naturalWidth || img.width;
                            canvas.height = img.naturalHeight || img.height;
                            const ctx = canvas.getContext('2d');
                            ctx.drawImage(img, 0, 0);
                            const dataUrl = canvas.toDataURL('image/png');
                            results.push({
                                page: parseInt(pageNum),
                                data: dataUrl
                            });
                        } catch (e) {
                            results.push({
                                page: parseInt(pageNum),
                                data: null,
                                error: e.message
                            });
                        }
                    }
                }
                
                return results;
                """
        
        saved_pages = set()
        failed_pages = []
        retry_delays = [2, 5, 10]  # Increasing delays for retries
        
        try:
            # First attempt - extract all images
            results = self.driver.execute_script(get_extraction_script())
            
            for result in results:
                page_num = result.get('page', 0)
                data_url = result.get('data')
                
                if data_url:
                    match = re.match(r'data:image/(\w+);base64,(.+)', data_url)
                    if match:
                        ext = match.group(1)
                        if ext == 'jpeg':
                            ext = 'jpg'
                        b64_data = match.group(2)
                        
                        image_path = chapter_dir / f"{page_num:03d}.{ext}"
                        with open(image_path, "wb") as f:
                            f.write(base64.b64decode(b64_data))
                        
                        saved_pages.add(page_num)
                        
                        if progress_callback:
                            progress_callback(len(saved_pages), total_pages)
                else:
                    failed_pages.append(page_num)
            
            # Retry failed pages
            for retry_attempt in range(self.max_retries):
                if not failed_pages:
                    break
                
                # Wait before retry with increasing delay
                delay = retry_delays[min(retry_attempt, len(retry_delays) - 1)]
                time.sleep(delay)
                
                # Retry extraction for failed pages
                retry_results = self.driver.execute_script(get_extraction_script(failed_pages))
                
                still_failed = []
                for result in retry_results:
                    page_num = result.get('page', 0)
                    data_url = result.get('data')
                    
                    if data_url:
                        match = re.match(r'data:image/(\w+);base64,(.+)', data_url)
                        if match:
                            ext = match.group(1)
                            if ext == 'jpeg':
                                ext = 'jpg'
                            b64_data = match.group(2)
                            
                            image_path = chapter_dir / f"{page_num:03d}.{ext}"
                            with open(image_path, "wb") as f:
                                f.write(base64.b64decode(b64_data))
                            
                            saved_pages.add(page_num)
                            
                            if progress_callback:
                                progress_callback(len(saved_pages), total_pages)
                    else:
                        still_failed.append(page_num)
                
                failed_pages = still_failed
            
            return len(saved_pages)
            
        except Exception:
            return len(saved_pages)
    
    def get_image_paths(self, chapter_dir: Path) -> list[Path]:
        """Get sorted list of image paths in a chapter directory"""
        if not chapter_dir.exists():
            return []
        
        # Get all image files
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
        images = [
            f for f in chapter_dir.iterdir() 
            if f.is_file() and f.suffix.lower() in image_extensions
        ]
        
        # Sort by filename (which should be numeric)
        return sorted(images, key=lambda p: p.stem)

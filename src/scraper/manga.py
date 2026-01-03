"""
Manga information and chapter extraction
"""

import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .models import MangaInfo, Chapter
from .browser import BrowserManager


class MangaScraper:
    """Scrapes manga info and chapter lists from kagane.org"""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser = browser_manager
        self.driver = browser_manager.get_driver()
    
    def scrape_manga(self, url: str) -> MangaInfo:
        """Scrape manga info and chapter list from the given URL"""
        
        self.driver.get(url)
        
        # Wait for content to load
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.font-bold"))
            )
        except TimeoutException:
            return MangaInfo()
        
        # Give extra time for JS to render
        time.sleep(2)
        
        # Extract manga info
        manga_info = self._extract_manga_info()
        
        # Click 18+ button if present (for erotica manga)
        self._accept_18plus_content()
        
        # Click dropdown to show ALL chapters
        self._select_all_chapters()
        
        # Close any ad tabs that may have opened
        self.browser.close_ad_tabs()
        
        # Extract chapters
        chapters = self._extract_chapters()
        manga_info.chapters = chapters
        
        return manga_info
    
    def _accept_18plus_content(self) -> None:
        """Click the 'Show all 18+ content' button if present"""
        try:
            button_18plus = self.driver.find_element(By.XPATH, 
                "//button[contains(text(), '18+') or contains(text(), 'Show all 18+')]"
            )
            button_18plus.click()
            time.sleep(1)
            
            # Close any ad tabs that may have opened
            self.browser.close_ad_tabs()
            
        except NoSuchElementException:
            # Button not present, manga is not erotica or already accepted
            pass
        except Exception:
            pass
    
    def _select_all_chapters(self) -> None:
        """Click the dropdown and select ALL to show all chapters"""
        try:
            # Remember original window handle
            original_window = self.driver.current_window_handle
            original_tab_count = len(self.driver.window_handles)
            
            # Find the dropdown button (shows "20" by default)
            dropdown_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[role='combobox']"))
            )
            
            # Click to open dropdown
            dropdown_button.click()
            time.sleep(0.5)
            
            # Close any new tabs that may have opened
            if len(self.driver.window_handles) > original_tab_count:
                for handle in self.driver.window_handles:
                    if handle != original_window:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                self.driver.switch_to.window(original_window)
                time.sleep(0.3)
                # Click dropdown again since new tab disrupted it
                dropdown_button.click()
                time.sleep(0.5)
            
            # Find and click the "All" option
            try:
                all_option = self.driver.find_element(By.XPATH, 
                    "//*[@role='option' and (text()='All' or .//span[text()='All'] or contains(text(), 'All'))]"
                )
                all_option.click()
            except Exception:
                # Try clicking by JavaScript
                self.driver.execute_script("""
                    const options = document.querySelectorAll('[role="option"]');
                    for (const opt of options) {
                        if (opt.textContent.trim() === 'All' || opt.textContent.includes('All')) {
                            opt.click();
                            return;
                        }
                    }
                """)
            
            # Wait for chapter list to reload
            time.sleep(1)
            
            # Close any new tabs again
            if len(self.driver.window_handles) > original_tab_count:
                for handle in self.driver.window_handles:
                    if handle != original_window:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                self.driver.switch_to.window(original_window)
            
        except TimeoutException:
            pass
        except Exception:
            pass
    
    def _extract_manga_info(self) -> MangaInfo:
        """Extract manga information from the page"""
        
        # Title
        title = ""
        try:
            title_elem = self.driver.find_element(By.CSS_SELECTOR, "h1.font-bold")
            title = title_elem.text.strip()
        except Exception:
            pass
        
        # Alternative titles
        alt_titles = []
        try:
            alt_container = self.driver.find_element(By.CSS_SELECTOR, "div.hidden.md\\:block p.text-muted-foreground")
            alt_spans = alt_container.find_elements(By.TAG_NAME, "span")
            for span in alt_spans:
                text = span.text.strip().rstrip(" /").strip()
                if text:
                    alt_titles.append(text)
        except Exception:
            pass
        
        # Cover URL (convert blob to base64 data URL)
        cover_url = ""
        try:
            # Use JavaScript to convert blob to base64
            cover_url = self.driver.execute_script("""
                const img = document.querySelector('div.flex-shrink-0 div.relative img');
                if (!img || !img.src) return '';
                
                try {
                    const canvas = document.createElement('canvas');
                    canvas.width = img.naturalWidth || img.width;
                    canvas.height = img.naturalHeight || img.height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                    return canvas.toDataURL('image/png');
                } catch (e) {
                    return img.src;  // Return original if conversion fails
                }
            """) or ""
        except Exception:
            pass
        
        # Author
        author = ""
        try:
            author_container = self.driver.find_element(By.CSS_SELECTOR, "div.hidden.md\\:block.mt-2 p.text-muted-foreground")
            author_spans = author_container.find_elements(By.TAG_NAME, "span")
            authors = []
            for span in author_spans:
                text = span.text.strip().rstrip(" /").strip()
                if text:
                    authors.append(text)
            author = " / ".join(authors)
        except Exception:
            pass
        
        # Description
        description = ""
        try:
            # Try JavaScript extraction for more reliability
            description = self.driver.execute_script("""
                const desc = document.querySelector('p.leading-relaxed');
                return desc ? desc.innerText.trim() : '';
            """) or ""
        except Exception:
            pass
        
        # Source
        source = ""
        try:
            # Try JavaScript to get the source badge text
            source = self.driver.execute_script("""
                const badge = document.querySelector('span[title^="Search by source:"]');
                return badge ? badge.innerText.trim() : '';
            """) or ""
        except Exception:
            pass
        
        # Is Erotica
        is_erotica = False
        try:
            self.driver.find_element(By.XPATH, "//span[contains(text(), 'Erotica')]")
            is_erotica = True
        except Exception:
            pass
        
        # Status (ENDED/ONGOING)
        status = ""
        try:
            # Look for the status in the flex container with icons
            status_container = self.driver.find_element(By.CSS_SELECTOR, "div.hidden.md\\:flex.flex-wrap.items-center.gap-4")
            status_spans = status_container.find_elements(By.CSS_SELECTOR, "span.text-foreground")
            for span in status_spans:
                text = span.text.strip()
                if text in ["ENDED", "ONGOING", "COMPLETED"]:
                    status = text
                    break
        except Exception:
            pass
        
        # Total chapters
        total_chapters = ""
        try:
            chapters_elem = self.driver.find_element(By.XPATH, "//span[contains(text(), 'chapters')]")
            text = chapters_elem.text
            match = re.search(r'(\d+)\s*chapters?', text)
            if match:
                total_chapters = match.group(1)
        except Exception:
            pass
        
        # Views
        views = ""
        try:
            # Look for the views span in the flex container
            status_container = self.driver.find_element(By.CSS_SELECTOR, "div.hidden.md\\:flex.flex-wrap.items-center.gap-4")
            views_spans = status_container.find_elements(By.CSS_SELECTOR, "span.text-foreground")
            for span in views_spans:
                text = span.text.strip()
                if 'views' in text.lower():
                    match = re.search(r'(\d+)', text)
                    if match:
                        views = match.group(1)
                    break
        except Exception:
            pass
        
        # Genres
        genres = []
        try:
            genre_badges = self.driver.find_elements(By.CSS_SELECTOR, "span[title^='Search by genre:']")
            for badge in genre_badges:
                genres.append(badge.text.strip())
            # Remove duplicates while preserving order
            genres = list(dict.fromkeys(genres))
        except Exception:
            pass
        
        return MangaInfo(
            title=title,
            alt_titles=alt_titles,
            cover_url=cover_url,
            author=author,
            description=description,
            source=source,
            is_erotica=is_erotica,
            status=status,
            total_chapters=total_chapters,
            views=views,
            genres=genres,
            chapters=[]
        )
    
    def _extract_chapters(self) -> list:
        """Extract chapter list from the page"""
        chapters = []
        
        try:
            chapter_divs = self.driver.find_elements(By.CSS_SELECTOR, "div[id^='chapter-']")
            
            for chapter_div in chapter_divs:
                chapter_id = chapter_div.get_attribute("id") or ""
                
                # Chapter number
                chapter_number = ""
                try:
                    number_span = chapter_div.find_element(By.CSS_SELECTOR, "div.w-10.h-10 span")
                    chapter_number = number_span.text.strip()
                except Exception:
                    pass
                
                # Chapter title
                chapter_title = ""
                try:
                    title_h3 = chapter_div.find_element(By.CSS_SELECTOR, "h3.font-semibold")
                    chapter_title = title_h3.text.strip()
                except Exception:
                    pass
                
                # Chapter URL
                chapter_url = ""
                try:
                    anchor = chapter_div.find_element(By.CSS_SELECTOR, "a[href*='/reader/']")
                    href = anchor.get_attribute("href") or ""
                    chapter_url = href
                except Exception:
                    pass
                
                # Date, pages, views
                chapter_date = ""
                chapter_pages = ""
                chapter_views = ""
                try:
                    info_div = chapter_div.find_element(By.CSS_SELECTOR, "div.flex.items-center.gap-3.text-xs")
                    info_text = info_div.text
                    
                    # Extract pages
                    pages_match = re.search(r'(\d+)\s*pages?', info_text)
                    if pages_match:
                        chapter_pages = pages_match.group(1)
                    
                    # Extract views
                    views_match = re.search(r'(\d+)\s*views?', info_text)
                    if views_match:
                        chapter_views = views_match.group(1)
                    
                    # Date is usually the first part
                    date_spans = info_div.find_elements(By.TAG_NAME, "span")
                    for span in date_spans:
                        text = span.text.strip()
                        if text and not re.search(r'\d+\s*(pages?|views?)', text):
                            chapter_date = text
                            break
                except Exception:
                    pass
                
                chapter = Chapter(
                    id=chapter_id,
                    number=chapter_number,
                    title=chapter_title,
                    url=chapter_url,
                    date=chapter_date,
                    pages=chapter_pages,
                    views=chapter_views
                )
                chapters.append(chapter)
                
        except Exception:
            pass
        
        return chapters

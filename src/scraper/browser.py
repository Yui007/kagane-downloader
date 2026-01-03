"""
Browser management using undetected-chromedriver
"""

import undetected_chromedriver as uc
from rich.console import Console

console = Console()


class BrowserManager:
    """Manages browser instance using undetected-chromedriver"""
    
    def __init__(self):
        self.driver = None
    
    def init_browser(self) -> uc.Chrome:
        """Initialize browser with undetected-chromedriver"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--headless=new')
        self.driver = uc.Chrome(options=options, use_subprocess=True)
        return self.driver
    
    def close_browser(self) -> None:
        """Close browser safely"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
    
    def get_driver(self) -> uc.Chrome:
        """Get the current driver instance"""
        if not self.driver:
            return self.init_browser()
        return self.driver
    
    def close_ad_tabs(self) -> None:
        """Close any tabs that are not kagane.org (ad tabs)"""
        if not self.driver:
            return
        
        try:
            original_window = self.driver.current_window_handle
            
            for handle in self.driver.window_handles:
                if handle != original_window:
                    self.driver.switch_to.window(handle)
                    current_url = self.driver.current_url
                    
                    # Close if not kagane.org
                    if 'kagane.org' not in current_url:
                        self.driver.close()
            
            # Switch back to original window
            self.driver.switch_to.window(original_window)
        except Exception:
            pass
    
    def __enter__(self):
        """Context manager entry"""
        self.init_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close_browser()
        return False

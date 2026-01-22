"""
Browser management using undetected-chromedriver
"""

import subprocess
import re
import os
import signal
import atexit
import undetected_chromedriver as uc
from rich.console import Console

console = Console()

# Track all browser instances for cleanup
_active_browsers: list["BrowserManager"] = []


def _cleanup_all_browsers():
    """Cleanup function called on program exit"""
    for browser in _active_browsers[:]:
        try:
            browser.close_browser()
        except Exception:
            pass


# Register cleanup on program exit
atexit.register(_cleanup_all_browsers)


def get_chrome_version() -> int | None:
    """Auto-detect installed Chrome version from system"""
    # Try Windows registry first
    try:
        import winreg
        for reg_path in [
            r"SOFTWARE\Google\Chrome\BLBeacon",
            r"SOFTWARE\WOW6432Node\Google\Chrome\BLBeacon",
        ]:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path)
                version, _ = winreg.QueryValueEx(key, "version")
                winreg.CloseKey(key)
                major_version = int(version.split(".")[0])
                return major_version
            except (FileNotFoundError, OSError):
                continue
    except ImportError:
        pass
    
    # Fallback: try running chrome --version
    try:
        chrome_paths = [
            "google-chrome",
            "chrome",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        for chrome_path in chrome_paths:
            try:
                result = subprocess.run(
                    [chrome_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    match = re.search(r"(\d+)\.", result.stdout)
                    if match:
                        return int(match.group(1))
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
    except Exception:
        pass
    
    return None


class BrowserManager:
    """Manages browser instance using undetected-chromedriver"""
    
    def __init__(self):
        self.driver = None
        self._browser_pid = None
        self._chromedriver_pid = None
    
    def init_browser(self) -> uc.Chrome:
        """Initialize browser with undetected-chromedriver"""
        # Close any existing browser first
        if self.driver:
            self.close_browser()
        
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--headless=new')
        
        # Auto-detect Chrome version for compatibility
        chrome_version = get_chrome_version()
        if chrome_version:
            console.print(f"[dim]Detected Chrome version: {chrome_version}[/]")
            self.driver = uc.Chrome(options=options, use_subprocess=True, version_main=chrome_version)
        else:
            # Let undetected-chromedriver try its own detection
            self.driver = uc.Chrome(options=options, use_subprocess=True)
        
        # Track PIDs for cleanup
        try:
            if hasattr(self.driver, 'browser_pid'):
                self._browser_pid = self.driver.browser_pid
            if hasattr(self.driver, 'service') and hasattr(self.driver.service, 'process'):
                self._chromedriver_pid = self.driver.service.process.pid
        except Exception:
            pass
        
        # Register this browser for cleanup
        if self not in _active_browsers:
            _active_browsers.append(self)
        
        return self.driver
    
    def close_browser(self) -> None:
        """Close browser safely with forceful cleanup"""
        if not self.driver:
            return
        
        # Step 1: Try graceful quit
        try:
            self.driver.quit()
        except Exception:
            pass
        
        # Step 2: Forcefully kill browser process if still running
        if self._browser_pid:
            self._kill_process_tree(self._browser_pid)
        
        # Step 3: Forcefully kill chromedriver process if still running
        if self._chromedriver_pid:
            self._kill_process_tree(self._chromedriver_pid)
        
        # Reset state
        self.driver = None
        self._browser_pid = None
        self._chromedriver_pid = None
        
        # Unregister from active browsers
        if self in _active_browsers:
            _active_browsers.remove(self)
    
    def _kill_process_tree(self, pid: int) -> None:
        """Kill a process and all its children"""
        try:
            if os.name == 'nt':  # Windows
                # Use taskkill to kill process tree
                subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', str(pid)],
                    capture_output=True,
                    timeout=5
                )
            else:  # Unix/Linux/Mac
                # Kill process group
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        except Exception:
            pass
    
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

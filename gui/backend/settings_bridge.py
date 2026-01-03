"""
Settings Bridge - Exposes config.py settings to QML
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import get_config, save_config


class SettingsBridge(QObject):
    """Bridge to expose settings to QML"""
    
    # Signals for property changes
    settingsChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = get_config()
    
    def _save(self):
        """Save config and emit change signal"""
        save_config(self._config)
        self.settingsChanged.emit()
    
    # Download Format
    @pyqtProperty(str, notify=settingsChanged)
    def downloadFormat(self):
        return self._config.download_format
    
    @downloadFormat.setter
    def downloadFormat(self, value):
        self._config.download_format = value
        self._save()
    
    # Keep Images
    @pyqtProperty(bool, notify=settingsChanged)
    def keepImages(self):
        return self._config.keep_images
    
    @keepImages.setter
    def keepImages(self, value):
        self._config.keep_images = value
        self._save()
    
    # Max Concurrent Chapters
    @pyqtProperty(int, notify=settingsChanged)
    def maxConcurrentChapters(self):
        return self._config.max_concurrent_chapters
    
    @maxConcurrentChapters.setter
    def maxConcurrentChapters(self, value):
        self._config.max_concurrent_chapters = value
        self._save()
    
    # Max Concurrent Images
    @pyqtProperty(int, notify=settingsChanged)
    def maxConcurrentImages(self):
        return self._config.max_concurrent_images
    
    @maxConcurrentImages.setter
    def maxConcurrentImages(self, value):
        self._config.max_concurrent_images = value
        self._save()
    
    # Max Display Chapters
    @pyqtProperty(int, notify=settingsChanged)
    def maxDisplayChapters(self):
        return self._config.max_display_chapters
    
    @maxDisplayChapters.setter
    def maxDisplayChapters(self, value):
        self._config.max_display_chapters = value
        self._save()
    
    # Download Directory
    @pyqtProperty(str, notify=settingsChanged)
    def downloadDirectory(self):
        return self._config.download_directory
    
    @downloadDirectory.setter
    def downloadDirectory(self, value):
        self._config.download_directory = value
        self._save()
    
    # Enable Logs
    @pyqtProperty(bool, notify=settingsChanged)
    def enableLogs(self):
        return self._config.enable_logs
    
    @enableLogs.setter
    def enableLogs(self, value):
        self._config.enable_logs = value
        self._save()
    
    # Image Load Delay
    @pyqtProperty(int, notify=settingsChanged)
    def imageLoadDelay(self):
        return self._config.image_load_delay
    
    @imageLoadDelay.setter
    def imageLoadDelay(self, value):
        self._config.image_load_delay = value
        self._save()
    
    # Max Retries
    @pyqtProperty(int, notify=settingsChanged)
    def maxRetries(self):
        return self._config.max_retries
    
    @maxRetries.setter
    def maxRetries(self, value):
        self._config.max_retries = value
        self._save()
    
    @pyqtSlot()
    def reload(self):
        """Reload settings from file"""
        self._config = get_config()
        self.settingsChanged.emit()

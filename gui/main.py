"""
Kagane Downloader - PyQt6 + QML GUI
"""

import sys
import os
from pathlib import Path

# Use Basic style to avoid Windows-specific control issues
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gui.backend import ScraperWorker, DownloadWorker, SettingsBridge
from src.scraper import Series, Book


class AppController(QObject):
    """Main controller bridging QML and Python"""
    
    # Signals for QML
    mangaLoaded = pyqtSignal(str, str, str, str, str, str, str, str, list, list)
    # title, author, description, source, status, views, chapters_count, cover_url, genres, chapters
    chaptersLoaded = pyqtSignal(list)  # List of chapter dicts
    loadingStarted = pyqtSignal()
    loadingFinished = pyqtSignal()
    loadingError = pyqtSignal(str)
    loadingProgress = pyqtSignal(str)
    
    downloadStarted = pyqtSignal()
    downloadProgress = pyqtSignal(int, int, str)  # current, total, message
    downloadChapterComplete = pyqtSignal(str, bool)  # chapter_number, success
    downloadFinished = pyqtSignal(int, int)  # success, total
    downloadError = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scraper_worker = None
        self._download_worker = None
        self._current_series = None
        self._books = []
    
    @pyqtSlot(str)
    def fetchManga(self, url):
        """Fetch manga info from URL using API"""
        if self._scraper_worker and self._scraper_worker.isRunning():
            return
        
        self.loadingStarted.emit()
        
        self._scraper_worker = ScraperWorker(url)
        self._scraper_worker.finished.connect(self._on_series_loaded)
        self._scraper_worker.error.connect(self._on_loading_error)
        self._scraper_worker.progress.connect(self._on_loading_progress)
        self._scraper_worker.start()
    
    def _on_series_loaded(self, series: Series):
        """Handle series loaded from API"""
        self._current_series = series
        self._books = series.series_books
        
        # Get genre names
        genre_names = [g.genre_name for g in series.genres if not g.is_spoiler]
        
        # Emit manga info to QML
        self.mangaLoaded.emit(
            series.title or "",
            "",  # Author not directly available in API
            series.description or "",
            series.format or "",  # Source replaced with format
            series.publication_status or series.upload_status or "",
            str(series.total_views or ""),
            str(series.current_books or len(series.series_books)),
            series.cover_url or "",  # Cover URL from series_covers
            genre_names,
            [book.chapter_no for book in series.series_books]
        )
        
        # Emit chapters as list of dicts
        chapters_data = []
        for i, book in enumerate(series.series_books):
            chapters_data.append({
                'index': i,
                'number': book.chapter_no,
                'title': book.title,
                'pages': str(book.page_count) if book.page_count else "-",
                'date': book.created_at[:10] if book.created_at else "-",  # Just the date part
                'selected': False
            })
        self.chaptersLoaded.emit(chapters_data)
        self.loadingFinished.emit()
    
    def _on_loading_error(self, error):
        """Handle loading error"""
        self.loadingError.emit(error)
        self.loadingFinished.emit()
    
    def _on_loading_progress(self, msg):
        """Handle loading progress"""
        self.loadingProgress.emit(msg)
    
    @pyqtSlot(list)
    def downloadChapters(self, selected_indices):
        """Download selected chapters"""
        if self._download_worker and self._download_worker.isRunning():
            return
        
        if not self._current_series or not self._books:
            self.downloadError.emit("No manga loaded")
            return
        
        # Get selected chapters
        selected = [self._books[i] for i in selected_indices if i < len(self._books)]
        
        if not selected:
            self.downloadError.emit("No chapters selected")
            return
        
        self.downloadStarted.emit()
        
        self._download_worker = DownloadWorker(self._current_series, selected)
        self._download_worker.progress.connect(lambda c, t, m: self.downloadProgress.emit(c, t, m))
        self._download_worker.chapterComplete.connect(lambda n, s: self.downloadChapterComplete.emit(n, s))
        self._download_worker.finished.connect(lambda s, t: self.downloadFinished.emit(s, t))
        self._download_worker.error.connect(lambda e: self.downloadError.emit(e))
        self._download_worker.start()
    
    @pyqtSlot()
    def stopDownload(self):
        """Stop current download"""
        if self._download_worker:
            self._download_worker.stop()
    
    @pyqtSlot()
    def stopLoading(self):
        """Stop current loading"""
        if self._scraper_worker:
            self._scraper_worker.stop()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Kagane Downloader")
    app.setOrganizationName("KaganeDownloader")
    
    # Create QML engine
    engine = QQmlApplicationEngine()
    
    # Create and expose controllers
    controller = AppController()
    settings = SettingsBridge()
    
    engine.rootContext().setContextProperty("appController", controller)
    engine.rootContext().setContextProperty("settings", settings)
    
    # Load QML
    qml_path = Path(__file__).parent / "qml" / "main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    
    if not engine.rootObjects():
        print("Failed to load QML")
        sys.exit(-1)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

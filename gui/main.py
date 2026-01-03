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
from src.scraper import MangaInfo, Chapter


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
        self._current_manga = None
        self._chapters = []
    
    @pyqtSlot(str)
    def fetchManga(self, url):
        """Fetch manga info from URL"""
        if self._scraper_worker and self._scraper_worker.isRunning():
            return
        
        self.loadingStarted.emit()
        
        self._scraper_worker = ScraperWorker(url)
        self._scraper_worker.finished.connect(self._on_manga_loaded)
        self._scraper_worker.error.connect(self._on_loading_error)
        self._scraper_worker.progress.connect(self._on_loading_progress)
        self._scraper_worker.start()
    
    def _on_manga_loaded(self, manga: MangaInfo):
        """Handle manga loaded"""
        self._current_manga = manga
        self._chapters = manga.chapters
        
        # Emit manga info to QML
        self.mangaLoaded.emit(
            manga.title or "",
            manga.author or "",
            manga.description or "",
            manga.source or "",
            manga.status or "",
            manga.views or "",
            str(manga.total_chapters or len(manga.chapters)),
            manga.cover_url or "",
            manga.genres,
            [ch.number for ch in manga.chapters]
        )
        
        # Emit chapters as list of dicts
        chapters_data = []
        for i, ch in enumerate(manga.chapters):
            chapters_data.append({
                'index': i,
                'number': ch.number,
                'title': ch.title,
                'pages': ch.pages or "-",
                'date': ch.date or "-",
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
        
        if not self._current_manga or not self._chapters:
            self.downloadError.emit("No manga loaded")
            return
        
        # Get selected chapters
        selected = [self._chapters[i] for i in selected_indices if i < len(self._chapters)]
        
        if not selected:
            self.downloadError.emit("No chapters selected")
            return
        
        self.downloadStarted.emit()
        
        self._download_worker = DownloadWorker(self._current_manga, selected)
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

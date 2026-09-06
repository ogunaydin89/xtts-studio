#!/usr/bin/env python3
"""
XTTS Studio - Native Qt6 WebEngine Isolated Desktop Window
Eliminates Google Chrome dependency. Completely self-contained in .venv.
"""
import sys
import os
import urllib.request

from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtGui import QIcon

BACKEND_STATUS_URL = "http://127.0.0.1:5222/api/status"

class StudioWindow(QMainWindow):
    def __init__(self, url, title="XTTS Studio", icon_path=None):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(1300, 850)
        self.setMinimumSize(850, 580)
        self._closing = False

        if icon_path and os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.profile = QWebEngineProfile("xtts-studio-isolated", self)
        self.profile.downloadRequested.connect(self._handle_download)
        self.page = QWebEnginePage(self.profile, self)

        self.browser = QWebEngineView(self)
        self.browser.setPage(self.page)
        self.browser.setUrl(QUrl(url))
        self.setCentralWidget(self.browser)

        # In-page "Quit" only shuts down the backend server; it has no way
        # to close this native Qt window. Poll for the backend going away
        # (backend-initiated shutdown, or a crash) and close ourselves.
        self._backend_watchdog = QTimer(self)
        self._backend_watchdog.timeout.connect(self._check_backend_alive)
        self._backend_watchdog.start(1500)

    def _handle_download(self, download):
        """Every synthesis is already saved permanently in ~/Music/AI_Voice
        by the backend, so the in-page WAV download button would otherwise
        just create a redundant duplicate copy. Cancel it rather than
        leaving the request unanswered, which QWebEngineView treats as
        silently doing nothing on click."""
        download.cancel()

    def _check_backend_alive(self):
        if self._closing:
            return
        try:
            with urllib.request.urlopen(BACKEND_STATUS_URL, timeout=1.5):
                pass
        except Exception:
            self._closing = True
            self._backend_watchdog.stop()
            self.close()

    def closeEvent(self, event):
        """Clean shutdown hook when user closes the window."""
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:5222/api/shutdown",
                data=b"{}",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=1.5):
                pass
        except Exception:
            pass
        event.accept()

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5222"
    title = sys.argv[2] if len(sys.argv) > 2 else "XTTS Studio"
    icon = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(__file__), "icon.svg")

    app = QApplication(sys.argv)
    app.setApplicationName(title)
    if os.path.isfile(icon):
        app.setWindowIcon(QIcon(icon))

    window = StudioWindow(url, title, icon)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

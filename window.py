#!/usr/bin/env python3
"""
XTTS Studio - Native Qt6 WebEngine Isolated Desktop Window
Eliminates Google Chrome dependency. Completely self-contained in .venv.
"""
import os
import socket
import sys
import urllib.request
import urllib.parse

from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtGui import QIcon


class StudioWindow(QMainWindow):
    def __init__(self, url, title="XTTS Studio", icon_path=None):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(1300, 850)
        self.setMinimumSize(850, 580)
        self._closing = False

        parsed = urllib.parse.urlparse(url)
        self._host = parsed.hostname or "127.0.0.1"
        self._port = parsed.port or 5222
        self._shutdown_url = f"http://{self._host}:{self._port}/api/shutdown"

        if icon_path and os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.profile = QWebEngineProfile("xtts-studio-isolated", self)
        self.page = QWebEnginePage(self.profile, self)
        self.page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanCloseWindows, True
        )
        self.page.windowCloseRequested.connect(self.close)

        self.browser = QWebEngineView(self)
        self.browser.setPage(self.page)
        self.browser.setUrl(QUrl(url))
        self.setCentralWidget(self.browser)

        # Kernel TCP socket check: completes in <0.1ms in the Linux kernel
        # listen backlog even while Python's GIL is busy running 8-core PyTorch
        # CPU inference, and only fails when the backend process actually exits.
        self._consecutive_failures = 0
        self._backend_watchdog = QTimer(self)
        self._backend_watchdog.timeout.connect(self._check_backend_alive)
        self._backend_watchdog.start(2000)

    def _check_backend_alive(self):
        if self._closing:
            return
        try:
            with socket.create_connection((self._host, self._port), timeout=0.5):
                self._consecutive_failures = 0
        except OSError:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 2:
                self._closing = True
                self._backend_watchdog.stop()
                self.close()

    def closeEvent(self, event):
        """Clean shutdown hook when user closes the window."""
        self._closing = True
        try:
            req = urllib.request.Request(
                self._shutdown_url,
                data=b"{}",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=1.0):
                pass
        except Exception:
            pass
        event.accept()


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5222"
    title = sys.argv[2] if len(sys.argv) > 2 else "XTTS Studio"
    icon = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
        os.path.dirname(__file__), "static", "icon.svg")

    app = QApplication(sys.argv)
    app.setApplicationName(title)
    # Wayland takes the xdg-shell app_id from the desktop file name; without
    # this Qt falls back to the interpreter basename ("python") and the window
    # never matches xtts-studio.desktop, so the taskbar shows a generic icon.
    app.setDesktopFileName("xtts-studio")
    if os.path.isfile(icon):
        app.setWindowIcon(QIcon(icon))

    window = StudioWindow(url, title, icon)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

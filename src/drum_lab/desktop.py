"""Fenêtre native avec moteur web embarqué ; aucun navigateur externe."""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import traceback
from pathlib import Path
from urllib.parse import urlsplit


def allowed_resource(address: str, server_port: int) -> bool:
    """Allow the app origin and embedded viewer assets, never remote requests."""
    url = urlsplit(address)
    if url.scheme == "http":
        return url.hostname == "127.0.0.1" and url.port == server_port
    # Chromium’s PDF viewer imports its UI modules from this internal host.
    if url.scheme == "chrome":
        return url.netloc == "resources"
    return url.scheme in {"data", "blob", "about", "qrc", "chrome-extension"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Song2Agostini — application locale")
    parser.add_argument("--smoke-test", action="store_true", help="ouvre la fenêtre et vérifie son chargement")
    parser.add_argument("--screenshot", type=Path, help="capture facultative du smoke test")
    parser.add_argument("--smoke-audio", type=Path, help="audio du test complet du runtime embarqué")
    parser.add_argument("--smoke-output", type=Path, help="dossier des sorties du test complet")
    parser.add_argument("--smoke-synthetic", action="store_true", help="marque l’audio de test comme synthétique")
    args = parser.parse_args(argv)
    if args.smoke_audio and (not args.smoke_test or not args.smoke_output):
        parser.error("--smoke-audio requiert --smoke-test et --smoke-output")
    # Set before importing the pipeline: resources and writable runtime differ.
    frozen_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    payload = (frozen_root / "runtime").resolve()
    if payload.is_dir():
        os.environ.setdefault("DRUM_LAB_RUNTIME_ROOT", str(payload))
    if getattr(sys, "frozen", False):
        os.environ.setdefault("DRUM_LAB_RESOURCE_ROOT", str(frozen_root / "source"))
    from PySide6.QtCore import QTimer, QUrl, QStandardPaths
    from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineUrlRequestInterceptor
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from .ui import Application, LocalServer

    qt = QApplication(sys.argv[:1])
    qt.setApplicationName("Song2Agostini")
    qt.setOrganizationName("DrumLab")
    storage = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
    application = Application(storage / "jobs")
    server = LocalServer(("127.0.0.1", 0), application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"

    class LocalOnly(QWebEngineUrlRequestInterceptor):
        def interceptRequest(self, info):
            if not allowed_resource(info.requestUrl().toString(), server.server_port):
                info.block(True)

    profile = QWebEngineProfile(qt)  # in-memory cookies, no permanent user profile
    interceptor = LocalOnly(profile)
    profile.setUrlRequestInterceptor(interceptor)
    profile.settings().setAttribute(profile.settings().WebAttribute.PdfViewerEnabled, True)
    profile.settings().setAttribute(profile.settings().WebAttribute.PluginsEnabled, True)
    windows = []

    class Page(QWebEnginePage):
        def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
            return (url.toString().startswith(origin + "/") or url.toString() == "about:blank"
                    or url.scheme() in {"qrc", "chrome-extension"})

        def createWindow(self, window_type):
            child = create_window("Partition de batterie")
            return child.centralWidget().page()

    def create_window(title="Song2Agostini"):
        window = QMainWindow()
        window.setWindowTitle(title)
        window.resize(1200, 850)
        view = QWebEngineView(window)
        view.setPage(Page(profile, view))
        window.setCentralWidget(view)
        windows.append(window)
        window.show()
        return window

    def download(request):
        downloads = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        destination, _ = QFileDialog.getSaveFileName(windows[0], "Enregistrer la partition",
                                                    str(Path(downloads) / request.downloadFileName()))
        if destination:
            request.setDownloadDirectory(str(Path(destination).parent))
            request.setDownloadFileName(Path(destination).name)
            request.accept()
        else:
            request.cancel()

    profile.downloadRequested.connect(download)
    window = create_window()
    view = window.centralWidget()
    exit_status = [0]
    if args.smoke_test:
        def loaded(ok):
            if not ok:
                exit_status[0] = 1
            def inspect():
                def checked(value):
                    if not value:
                        exit_status[0] = 1
                    if args.screenshot:
                        args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                        view.grab().save(str(args.screenshot))
                    if not value or not args.smoke_audio:
                        qt.quit()
                        return
                    result = {}
                    def generate_test():
                        try:
                            from .pipeline import generate
                            generated = generate(args.smoke_audio, args.smoke_output,
                                                 config={"separate_drums": True, "compact": True,
                                                         "grid_engine": "beat_this"},
                                                 title=("Test technique — brouillon" if args.smoke_synthetic else args.smoke_audio.stem),
                                                 synthetic=args.smoke_synthetic)
                            result["report"] = {"status": "passed", "result": generated,
                                                "frozen": bool(getattr(sys, "frozen", False))}
                        except Exception:
                            result["report"] = {"status": "failed", "error": traceback.format_exc()}
                    threading.Thread(target=generate_test, daemon=True).start()
                    def wait_for_test():
                        if "report" not in result:
                            QTimer.singleShot(500, wait_for_test)
                            return
                        args.smoke_output.mkdir(parents=True, exist_ok=True)
                        (args.smoke_output / "desktop-smoke.json").write_text(json.dumps(result["report"], indent=2))
                        exit_status[0] = 0 if result["report"]["status"] == "passed" else 1
                        qt.quit()
                    QTimer.singleShot(500, wait_for_test)
                view.page().runJavaScript("Boolean(document.getElementById('audio') && document.getElementById('generate'))", checked)
            QTimer.singleShot(800, inspect)
        view.loadFinished.connect(loaded)
        QTimer.singleShot(1800000 if args.smoke_audio else 20000,
                          lambda: (exit_status.__setitem__(0, 1), qt.quit()))
    view.load(QUrl(origin + "/"))
    try:
        result = qt.exec()
    finally:
        server.shutdown()
        server.server_close()
        application.close()
        # Delete pages before the shared profile (Qt WebEngine lifetime contract).
        for item in windows:
            item.centralWidget().setPage(QWebEnginePage(item.centralWidget()))
    return exit_status[0] or result


if __name__ == "__main__":
    raise SystemExit(main())

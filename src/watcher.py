import os
import time
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class LogFileHandler(FileSystemEventHandler):
    """Watches a directory for new/modified .log and .txt files."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self._debounce = {}
        self._debounce_seconds = 2

    def _should_process(self, path: str) -> bool:
        ext = Path(path).suffix.lower()
        if ext not in (".log", ".txt"):
            return False
        now = time.time()
        last = self._debounce.get(path, 0)
        if now - last < self._debounce_seconds:
            return False
        self._debounce[path] = now
        return True

    def on_created(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            time.sleep(0.5)
            self.callback(event.src_path, "created")

    def on_modified(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            time.sleep(0.5)
            self.callback(event.src_path, "modified")


class DirectoryWatcher:
    """Manages a watchdog Observer on a target directory."""

    def __init__(self, watch_dir: str, callback):
        self.watch_dir = watch_dir
        self.callback = callback
        self._observer = None
        self._thread = None

    def start(self):
        if self._observer is not None:
            return

        Path(self.watch_dir).mkdir(parents=True, exist_ok=True)
        handler = LogFileHandler(self.callback)
        self._observer = Observer()
        self._observer.schedule(handler, self.watch_dir, recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def stop(self):
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

    def scan_existing(self) -> dict[str, str]:
        """Read all existing .log/.txt files in the watched directory."""
        logs = {}
        watch_path = Path(self.watch_dir)
        if watch_path.exists():
            for f in watch_path.iterdir():
                if f.suffix.lower() in (".log", ".txt") and f.is_file():
                    try:
                        logs[f.name] = f.read_text(errors="replace")
                    except OSError:
                        pass
        return logs

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

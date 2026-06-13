"""Directory watcher for automatic log file ingestion.

Uses the ``watchdog`` library to monitor a directory for new or modified
``.log`` and ``.txt`` files.  A debounce mechanism prevents duplicate
callbacks when the OS fires rapid-fire modification events for a single
write operation.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger: logging.Logger = logging.getLogger(__name__)


class LogFileHandler(FileSystemEventHandler):
    """Filesystem event handler that filters for log files with debounce.

    Only ``.log`` and ``.txt`` files are forwarded to the callback.
    Rapid re-fires for the same path within ``DEBOUNCE_SECONDS`` are
    silently dropped.

    Attributes:
        VALID_EXTENSIONS: File suffixes accepted for processing.
        DEBOUNCE_SECONDS: Minimum interval between callbacks for the
            same file path.
    """

    VALID_EXTENSIONS: set[str] = {".log", ".txt"}
    DEBOUNCE_SECONDS: int = 2

    def __init__(self, callback: Callable[[str, str], None]) -> None:
        """Initialise the handler with a user-supplied callback.

        Args:
            callback: Function called with ``(file_path, event_type)``
                where *event_type* is ``"created"`` or ``"modified"``.
        """
        super().__init__()
        self.callback: Callable[[str, str], None] = callback
        self._debounce: dict[str, float] = {}

    def _should_process(self, path: str) -> bool:
        """Determine whether a filesystem event should trigger a callback.

        Args:
            path: Absolute path of the file that triggered the event.

        Returns:
            ``True`` if the file has a valid extension and enough time
            has elapsed since the last callback for the same path.
        """
        ext: str = Path(path).suffix.lower()
        if ext not in self.VALID_EXTENSIONS:
            return False
        now: float = time.time()
        last: float = self._debounce.get(path, 0)
        if now - last < self.DEBOUNCE_SECONDS:
            return False
        self._debounce[path] = now
        return True

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle a file-creation event.

        Args:
            event: Watchdog event containing the source path.
        """
        if not event.is_directory and self._should_process(event.src_path):
            time.sleep(0.5)
            self.callback(event.src_path, "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle a file-modification event.

        Args:
            event: Watchdog event containing the source path.
        """
        if not event.is_directory and self._should_process(event.src_path):
            time.sleep(0.5)
            self.callback(event.src_path, "modified")


class DirectoryWatcher:
    """High-level wrapper around a ``watchdog.Observer``.

    Creates the watch directory if it does not exist, schedules a
    ``LogFileHandler``, and exposes start/stop lifecycle methods plus
    a one-shot ``scan_existing`` for initial ingestion.

    Args:
        watch_dir: Absolute path to the directory to monitor.
        callback: Function called with ``(file_path, event_type)``.
    """

    def __init__(self, watch_dir: str, callback: Callable[[str, str], None]) -> None:
        """Initialise the watcher without starting the observer.

        Args:
            watch_dir: Directory path to watch for log files.
            callback: Function invoked when a log file is created or
                modified, receiving ``(path, event_type)``.
        """
        self.watch_dir: str = watch_dir
        self.callback: Callable[[str, str], None] = callback
        self._observer: Observer | None = None

    def start(self) -> None:
        """Start watching the directory for file-system events.

        Creates the directory if it does not already exist.  Calling
        ``start()`` when the observer is already running is a no-op.
        """
        if self._observer is not None:
            return

        Path(self.watch_dir).mkdir(parents=True, exist_ok=True)
        handler: LogFileHandler = LogFileHandler(self.callback)
        self._observer = Observer()
        self._observer.schedule(handler, self.watch_dir, recursive=False)
        self._observer.daemon = True
        self._observer.start()
        logger.info("Started watching directory: %s", self.watch_dir)

    def stop(self) -> None:
        """Stop the observer and release its thread.

        Safe to call when the observer is not running.
        """
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("Stopped watching directory: %s", self.watch_dir)

    def scan_existing(self) -> dict[str, str]:
        """Read all existing log files in the watched directory.

        Iterates non-recursively over the watch directory and reads
        every file whose suffix is in ``LogFileHandler.VALID_EXTENSIONS``.
        Files that cannot be read (e.g. permission denied) are silently
        skipped.

        Returns:
            Mapping of filename to file content for each readable log
            file found.
        """
        logs: dict[str, str] = {}
        watch_path: Path = Path(self.watch_dir)
        if watch_path.exists():
            for f in watch_path.iterdir():
                if f.suffix.lower() in LogFileHandler.VALID_EXTENSIONS and f.is_file():
                    try:
                        logs[f.name] = f.read_text(errors="replace")
                    except OSError:
                        logger.warning("Could not read file: %s", f)
        return logs

    @property
    def is_running(self) -> bool:
        """Check whether the observer thread is alive.

        Returns:
            ``True`` if the observer has been started and its thread
            is still running.
        """
        return self._observer is not None and self._observer.is_alive()

"""Tests for watcher.py — LogFileHandler and DirectoryWatcher.

Uses ``tmp_path`` fixtures for filesystem isolation and follows the
AAA (Arrange-Act-Assert) pattern throughout.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from watcher import DirectoryWatcher, LogFileHandler


class TestLogFileHandler:
    """Verify file filtering, extension checks, and debounce logic."""

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("/tmp/test.log", True),
            ("/tmp/test.txt", True),
            ("/tmp/test.py", False),
            ("/tmp/test.json", False),
            ("/tmp/test.csv", False),
        ],
    )
    def test_should_process_filters_by_extension(
        self, filename: str, expected: bool
    ) -> None:
        """Only ``.log`` and ``.txt`` files should be accepted."""
        handler: LogFileHandler = LogFileHandler(callback=lambda p, e: None)
        assert handler._should_process(filename) is expected

    def test_debounce_prevents_rapid_reprocessing(self) -> None:
        """A second call for the same path within the debounce window should be rejected."""
        # Arrange
        handler: LogFileHandler = LogFileHandler(callback=lambda p, e: None)

        # Act / Assert
        assert handler._should_process("/tmp/test.log") is True
        assert handler._should_process("/tmp/test.log") is False

    def test_debounce_allows_different_files(self) -> None:
        """Distinct file paths should each be processed independently."""
        handler: LogFileHandler = LogFileHandler(callback=lambda p, e: None)
        assert handler._should_process("/tmp/a.log") is True
        assert handler._should_process("/tmp/b.log") is True

    def test_on_created_invokes_callback_for_log_file(self) -> None:
        """A file-creation event for a ``.log`` file should trigger the callback."""
        # Arrange
        cb: MagicMock = MagicMock()
        handler: LogFileHandler = LogFileHandler(callback=cb)
        handler.DEBOUNCE_SECONDS = 0

        event: MagicMock = MagicMock()
        event.is_directory = False
        event.src_path = "/tmp/test.log"

        # Act
        handler.on_created(event)

        # Assert
        cb.assert_called_once_with("/tmp/test.log", "created")

    def test_on_created_ignores_directories(self) -> None:
        """Directory-creation events should not trigger the callback."""
        cb: MagicMock = MagicMock()
        handler: LogFileHandler = LogFileHandler(callback=cb)

        event: MagicMock = MagicMock()
        event.is_directory = True
        event.src_path = "/tmp/logs"

        handler.on_created(event)
        cb.assert_not_called()

    def test_on_modified_invokes_callback_for_txt_file(self) -> None:
        """A file-modification event for a ``.txt`` file should trigger the callback."""
        cb: MagicMock = MagicMock()
        handler: LogFileHandler = LogFileHandler(callback=cb)
        handler.DEBOUNCE_SECONDS = 0

        event: MagicMock = MagicMock()
        event.is_directory = False
        event.src_path = "/tmp/test.txt"

        handler.on_modified(event)
        cb.assert_called_once_with("/tmp/test.txt", "modified")

    def test_on_modified_ignores_non_log_extensions(self) -> None:
        """Modification events for unsupported extensions should be ignored."""
        cb: MagicMock = MagicMock()
        handler: LogFileHandler = LogFileHandler(callback=cb)

        event: MagicMock = MagicMock()
        event.is_directory = False
        event.src_path = "/tmp/test.py"

        handler.on_modified(event)
        cb.assert_not_called()


class TestDirectoryWatcher:
    """Verify scan, start/stop lifecycle, and filesystem interactions."""

    def test_scan_existing_reads_only_log_files(self, tmp_path: Path) -> None:
        """Only ``.log`` and ``.txt`` files should be returned by scan."""
        # Arrange
        (tmp_path / "router.log").write_text("line1\nline2")
        (tmp_path / "switch.txt").write_text("entry1")
        (tmp_path / "notes.md").write_text("ignore me")

        watcher: DirectoryWatcher = DirectoryWatcher(
            str(tmp_path), callback=lambda p, e: None
        )

        # Act
        result: dict[str, str] = watcher.scan_existing()

        # Assert
        assert "router.log" in result
        assert "switch.txt" in result
        assert "notes.md" not in result
        assert result["router.log"] == "line1\nline2"

    def test_scan_existing_returns_empty_for_empty_directory(
        self, tmp_path: Path
    ) -> None:
        """An empty directory should yield an empty dict."""
        watcher: DirectoryWatcher = DirectoryWatcher(
            str(tmp_path), callback=lambda p, e: None
        )
        assert watcher.scan_existing() == {}

    def test_scan_existing_returns_empty_for_missing_directory(
        self, tmp_path: Path
    ) -> None:
        """A nonexistent directory should yield an empty dict without error."""
        watcher: DirectoryWatcher = DirectoryWatcher(
            str(tmp_path / "nope"), callback=lambda p, e: None
        )
        assert watcher.scan_existing() == {}

    def test_is_running_returns_false_before_start(self, tmp_path: Path) -> None:
        """A newly created watcher should not be running."""
        watcher: DirectoryWatcher = DirectoryWatcher(
            str(tmp_path), callback=lambda p, e: None
        )
        assert watcher.is_running is False

    def test_start_and_stop_lifecycle(self, tmp_path: Path) -> None:
        """Starting and stopping should toggle ``is_running`` correctly."""
        watcher: DirectoryWatcher = DirectoryWatcher(
            str(tmp_path), callback=lambda p, e: None
        )
        watcher.start()
        assert watcher.is_running is True
        watcher.stop()
        assert watcher.is_running is False

    def test_start_is_idempotent(self, tmp_path: Path) -> None:
        """Calling ``start()`` twice should not create a second observer."""
        watcher: DirectoryWatcher = DirectoryWatcher(
            str(tmp_path), callback=lambda p, e: None
        )
        watcher.start()
        observer_ref = watcher._observer
        watcher.start()
        assert watcher._observer is observer_ref
        watcher.stop()

    def test_stop_before_start_is_safe(self, tmp_path: Path) -> None:
        """Calling ``stop()`` before ``start()`` should not raise."""
        watcher: DirectoryWatcher = DirectoryWatcher(
            str(tmp_path), callback=lambda p, e: None
        )
        watcher.stop()

    def test_start_creates_missing_directory(self, tmp_path: Path) -> None:
        """``start()`` should create the watch directory if it does not exist."""
        watch_dir: Path = tmp_path / "new_watch_dir"
        assert not watch_dir.exists()
        watcher: DirectoryWatcher = DirectoryWatcher(
            str(watch_dir), callback=lambda p, e: None
        )
        watcher.start()
        assert watch_dir.exists()
        watcher.stop()

    def test_scan_existing_skips_unreadable_files(self, tmp_path: Path) -> None:
        """Files with denied read permissions should be silently skipped."""
        # Arrange
        log_file: Path = tmp_path / "protected.log"
        log_file.write_text("secret data")
        log_file.chmod(0o000)

        watcher: DirectoryWatcher = DirectoryWatcher(
            str(tmp_path), callback=lambda p, e: None
        )

        # Act
        result: dict[str, str] = watcher.scan_existing()

        # Assert
        assert "protected.log" not in result

        # Cleanup
        log_file.chmod(0o644)

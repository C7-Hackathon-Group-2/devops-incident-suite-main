"""Tests for watcher.py — LogFileHandler and DirectoryWatcher."""

import os
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from watcher import LogFileHandler, DirectoryWatcher


# ---------------------------------------------------------------------------
# LogFileHandler
# ---------------------------------------------------------------------------

class TestLogFileHandler:
    def test_should_process_log_file(self):
        handler = LogFileHandler(callback=lambda p, e: None)
        assert handler._should_process("/tmp/test.log") is True

    def test_should_process_txt_file(self):
        handler = LogFileHandler(callback=lambda p, e: None)
        assert handler._should_process("/tmp/test.txt") is True

    def test_should_not_process_non_log_file(self):
        handler = LogFileHandler(callback=lambda p, e: None)
        assert handler._should_process("/tmp/test.py") is False
        assert handler._should_process("/tmp/test.json") is False
        assert handler._should_process("/tmp/test.csv") is False

    def test_debounce_prevents_rapid_reprocessing(self):
        handler = LogFileHandler(callback=lambda p, e: None)
        assert handler._should_process("/tmp/test.log") is True
        assert handler._should_process("/tmp/test.log") is False

    def test_debounce_allows_different_files(self):
        handler = LogFileHandler(callback=lambda p, e: None)
        assert handler._should_process("/tmp/a.log") is True
        assert handler._should_process("/tmp/b.log") is True

    def test_on_created_calls_callback_for_log_file(self):
        cb = MagicMock()
        handler = LogFileHandler(callback=cb)
        handler._debounce_seconds = 0

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/tmp/test.log"

        handler.on_created(event)
        cb.assert_called_once_with("/tmp/test.log", "created")

    def test_on_created_skips_directory(self):
        cb = MagicMock()
        handler = LogFileHandler(callback=cb)

        event = MagicMock()
        event.is_directory = True
        event.src_path = "/tmp/logs"

        handler.on_created(event)
        cb.assert_not_called()

    def test_on_modified_calls_callback_for_log_file(self):
        cb = MagicMock()
        handler = LogFileHandler(callback=cb)
        handler._debounce_seconds = 0

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/tmp/test.txt"

        handler.on_modified(event)
        cb.assert_called_once_with("/tmp/test.txt", "modified")

    def test_on_modified_skips_non_log(self):
        cb = MagicMock()
        handler = LogFileHandler(callback=cb)

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/tmp/test.py"

        handler.on_modified(event)
        cb.assert_not_called()


# ---------------------------------------------------------------------------
# DirectoryWatcher
# ---------------------------------------------------------------------------

class TestDirectoryWatcher:
    def test_scan_existing_reads_log_files(self, tmp_path):
        (tmp_path / "router.log").write_text("line1\nline2")
        (tmp_path / "switch.txt").write_text("entry1")
        (tmp_path / "notes.md").write_text("ignore me")

        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p, e: None)
        result = watcher.scan_existing()

        assert "router.log" in result
        assert "switch.txt" in result
        assert "notes.md" not in result
        assert result["router.log"] == "line1\nline2"

    def test_scan_existing_empty_dir(self, tmp_path):
        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p, e: None)
        result = watcher.scan_existing()
        assert result == {}

    def test_scan_existing_nonexistent_dir(self, tmp_path):
        watcher = DirectoryWatcher(str(tmp_path / "nope"), callback=lambda p, e: None)
        result = watcher.scan_existing()
        assert result == {}

    def test_is_running_false_initially(self, tmp_path):
        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p, e: None)
        assert watcher.is_running is False

    def test_start_and_stop(self, tmp_path):
        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p, e: None)
        watcher.start()
        assert watcher.is_running is True
        watcher.stop()
        assert watcher.is_running is False

    def test_start_is_idempotent(self, tmp_path):
        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p, e: None)
        watcher.start()
        observer1 = watcher._observer
        watcher.start()
        assert watcher._observer is observer1
        watcher.stop()

    def test_stop_when_not_started_is_safe(self, tmp_path):
        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p, e: None)
        watcher.stop()  # should not raise

    def test_start_creates_directory_if_missing(self, tmp_path):
        watch_dir = tmp_path / "new_watch_dir"
        assert not watch_dir.exists()
        watcher = DirectoryWatcher(str(watch_dir), callback=lambda p, e: None)
        watcher.start()
        assert watch_dir.exists()
        watcher.stop()

    def test_scan_existing_skips_unreadable_files(self, tmp_path):
        log_file = tmp_path / "protected.log"
        log_file.write_text("secret data")
        log_file.chmod(0o000)

        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p, e: None)
        result = watcher.scan_existing()

        assert "protected.log" not in result

        log_file.chmod(0o644)

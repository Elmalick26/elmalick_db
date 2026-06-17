"""Q1 — background-worker shutdown on application close.

These windows are embedded in the main dashboard (their central widget is
reparented), so their own closeEvent never fires. The main window calls
``stop_background_workers()`` on shutdown to stop any running QThread before the
shared DB pool is closed, avoiding "QThread: Destroyed while running" crashes.

Constructed via ``__new__`` to avoid spinning up a real Qt window.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest


def _running_worker():
    w = MagicMock()
    w.isRunning.return_value = True
    return w


def _idle_worker():
    w = MagicMock()
    w.isRunning.return_value = False
    return w


def _assert_stopped(worker):
    worker.requestInterruption.assert_called_once()
    worker.quit.assert_called_once()
    worker.wait.assert_called_once()


def _assert_not_stopped(worker):
    worker.quit.assert_not_called()
    worker.wait.assert_not_called()


# ---------------------------------------------------------------------------
# Per-window stop_background_workers
# ---------------------------------------------------------------------------


class TestAnalyticsDashboardStop:
    def _win(self, worker, report_worker):
        from analytics_dashboard import AnalyticsDashboardWindow

        w = AnalyticsDashboardWindow.__new__(AnalyticsDashboardWindow)
        w._worker = worker
        w._report_worker = report_worker
        return w

    def test_stops_both_running_workers(self):
        worker, report = _running_worker(), _running_worker()
        self._win(worker, report).stop_background_workers()
        _assert_stopped(worker)
        _assert_stopped(report)

    def test_idle_workers_left_alone(self):
        worker, report = _idle_worker(), _idle_worker()
        self._win(worker, report).stop_background_workers()
        _assert_not_stopped(worker)
        _assert_not_stopped(report)

    def test_none_workers_are_safe(self):
        # Should not raise when workers were never created.
        self._win(None, None).stop_background_workers()


class TestAdvancedReportsStop:
    def _win(self, worker):
        from advanced_reports import AdvancedReportsWindow

        w = AdvancedReportsWindow.__new__(AdvancedReportsWindow)
        w.worker = worker  # production sets self.worker = None in __init__
        return w

    def test_stops_running_worker(self):
        worker = _running_worker()
        self._win(worker).stop_background_workers()
        _assert_stopped(worker)

    def test_no_worker_is_safe(self):
        self._win(None).stop_background_workers()  # None worker → skip


class TestCommunicationStop:
    def _win(self, worker):
        from communication_ui import CommunicationWindow

        w = CommunicationWindow.__new__(CommunicationWindow)
        w.worker = worker
        return w

    def test_stops_running_worker(self):
        worker = _running_worker()
        self._win(worker).stop_background_workers()
        _assert_stopped(worker)

    def test_no_worker_is_safe(self):
        self._win(None).stop_background_workers()


class TestYearEndMigrationStop:
    def _win(self, thread):
        from year_end_migration import MigrationWindow

        w = MigrationWindow.__new__(MigrationWindow)
        w.calc_thread = thread
        return w

    def test_stops_running_thread(self):
        thread = _running_worker()
        self._win(thread).stop_background_workers()
        _assert_stopped(thread)

    def test_no_thread_is_safe(self):
        self._win(None).stop_background_workers()


# ---------------------------------------------------------------------------
# MainWindow.closeEvent — stops module workers BEFORE closing the DB pool
# ---------------------------------------------------------------------------


class TestMainWindowCloseEvent:
    """Invoke closeEvent as a plain function on a fake self to avoid Qt setup."""

    def _call_close(self, module_windows):
        from types import SimpleNamespace
        from unittest.mock import patch

        import main_dashbord
        from main_dashbord import MainWindow

        fake_self = SimpleNamespace(module_windows=module_windows)  # no backup_system attr
        event = MagicMock()
        with patch.object(main_dashbord.DatabaseManager, "close_pool") as close_pool:
            MainWindow.closeEvent(fake_self, event)
        return close_pool, event

    def test_stops_module_workers_then_closes_pool(self):
        module = MagicMock()
        close_pool, event = self._call_close({"analytics": module})
        module.stop_background_workers.assert_called_once()
        close_pool.assert_called_once()
        event.accept.assert_called_once()

    def test_module_without_hook_is_skipped(self):
        # An object lacking stop_background_workers must not break shutdown.
        class NoHook:
            pass

        close_pool, event = self._call_close({"x": NoHook()})
        close_pool.assert_called_once()
        event.accept.assert_called_once()

    def test_worker_stop_error_does_not_block_pool_close(self):
        module = MagicMock()
        module.stop_background_workers.side_effect = RuntimeError("boom")
        close_pool, event = self._call_close({"x": module})
        # Even if a module errors, the pool must still close and the app exit.
        close_pool.assert_called_once()
        event.accept.assert_called_once()

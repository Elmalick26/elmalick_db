"""P2 — pagination logic for the student list (ui_styles.PaginationWidget).

The student list is paginated server-side (list_students LIMIT/OFFSET +
count_students). These tests lock the widget's offset/page math without a Qt
event loop: built via __new__ with _refresh_ui stubbed (it only updates labels).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ui_styles import PaginationWidget


def _pager(page_size=50, total=0, page=0):
    p = PaginationWidget.__new__(PaginationWidget)
    p.page_size = page_size
    p._current_page = page
    p._total = total
    p._refresh_ui = lambda: None  # skip Qt label/button updates
    return p


class TestOffset:
    def test_first_page_offset_zero(self):
        assert _pager(page_size=50, page=0).current_offset() == 0

    def test_offset_is_page_times_size(self):
        assert _pager(page_size=50, page=3).current_offset() == 150

    def test_offset_respects_page_size(self):
        assert _pager(page_size=25, page=2).current_offset() == 50


class TestTotalPages:
    def test_zero_total_is_one_page(self):
        assert _pager(total=0)._total_pages() == 1

    def test_exact_multiple(self):
        assert _pager(page_size=50, total=100)._total_pages() == 2

    def test_partial_page_rounds_up(self):
        assert _pager(page_size=50, total=101)._total_pages() == 3

    def test_single_partial_page(self):
        assert _pager(page_size=50, total=30)._total_pages() == 1


class TestSetTotalAndReset:
    def test_set_total_clamps_when_results_shrink(self):
        p = _pager(page_size=50, total=200, page=3)  # was on page 4 (offset 150)
        p.set_total(60)  # now only 2 pages (0,1)
        assert p._current_page == 1
        assert p.current_offset() == 50

    def test_set_total_negative_floored_to_zero(self):
        p = _pager(total=10)
        p.set_total(-5)
        assert p._total == 0

    def test_reset_returns_to_first_page(self):
        p = _pager(page_size=50, total=500, page=7)
        p.reset()
        assert p._current_page == 0
        assert p.current_offset() == 0

"""Snapshot test for the test widget."""
from unittest.mock import MagicMock
import pytest
from custom_components.eink.renderer import render_layout


def _coord():
    c = MagicMock()
    c._image_indices = {}
    c._image_lists = {}
    c.dither = "floyd-steinberg"
    return c


async def test_test_widget_snapshot(hass, assert_png_snapshot):
    widgets = [{"type": "test", "row": 0, "col": 0, "row_span": 3, "col_span": 4, "config": {}}]
    png = await render_layout(hass, widgets, _coord())
    assert_png_snapshot(png, "test_widget_full")

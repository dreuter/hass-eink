"""Golden master tests for the weather widget."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.eink.renderer import render_layout


def _coord():
    c = MagicMock()
    c._image_indices = {}
    c._image_lists = {}
    c.dither = "floyd-steinberg"
    return c


CONDITIONS = ["partlycloudy", "windy"]
SIZES = [(1, 1), (3, 2), (3, 4)]


from tests.conftest import assert_no_bleed

@pytest.mark.parametrize("condition", CONDITIONS)
@pytest.mark.parametrize("row_span,col_span", SIZES)
async def test_weather_snapshot(hass, assert_png_snapshot, condition, row_span, col_span):
    hass.states.async_set(
        "weather.home", condition,
        {"temperature": 18.5, "temperature_unit": "°C"},
    )
    widgets = [{"type": "weather", "row": 0, "col": 0,
                "row_span": row_span, "col_span": col_span,
                "config": {"entity_id": "weather.home"}}]
    png = await render_layout(hass, widgets, _coord())
    assert_no_bleed(png, widgets)
    assert_png_snapshot(png, f"weather_{condition}_{row_span}x{col_span}")

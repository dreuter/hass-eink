"""Golden master tests for the weather widget using the cat icon set."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import SupportsResponse

from custom_components.eink.renderer import render_layout
from tests.conftest import assert_no_bleed


def _coord():
    c = MagicMock()
    c._image_indices = {}
    c._image_lists = {}
    c.dither = "floyd-steinberg"
    return c


DAILY_FORECAST = {"weather.home": {"forecast": [{
    "datetime": "2026-04-13T00:00:00+02:00",
    "condition": "sunny",
    "temperature": 22.0,
    "templow": 8.0,
    "precipitation": 0.0,
    "precipitation_probability": 10,
    "wind_speed": 10.0,
    "wind_bearing": 90,
}]}}

CONDITIONS = ["sunny", "rainy", "snowy", "partlycloudy"]
SIZES = [(1, 1), (3, 2)]


@pytest.mark.parametrize("condition", CONDITIONS)
@pytest.mark.parametrize("row_span,col_span", SIZES)
async def test_cat_icon_set_snapshot(hass, assert_png_snapshot, condition, row_span, col_span):
    hass.states.async_set(
        "weather.home", condition,
        {
            "temperature": 18.5, "temperature_unit": "°C",
            "humidity": 65, "pressure": 1015.0, "pressure_unit": "hPa",
            "wind_speed": 10.0, "wind_speed_unit": "km/h", "wind_bearing": 90,
        },
    )
    hass.services.async_register(
        "weather", "get_forecasts", AsyncMock(return_value=DAILY_FORECAST),
        supports_response=SupportsResponse.ONLY,
    )
    widgets = [{"type": "weather", "row": 0, "col": 0,
                "row_span": row_span, "col_span": col_span,
                "config": {"entity_id": "weather.home", "icon_set": "cat"}}]
    png = await render_layout(hass, widgets, _coord())
    assert_no_bleed(png, widgets)
    assert_png_snapshot(png, f"cat_icons_{condition}_{row_span}x{col_span}")

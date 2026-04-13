"""Golden master tests for the weather widget."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import SupportsResponse

from custom_components.eink.renderer import render_layout


def _coord():
    c = MagicMock()
    c._image_indices = {}
    c._image_lists = {}
    c.dither = "floyd-steinberg"
    return c


CONDITIONS = ["partlycloudy", "windy"]
SIZES = [(1, 1), (3, 2), (3, 4)]

DAILY_FORECAST = {"weather.home": {"forecast": [{
    "datetime": "2026-04-13T00:00:00+02:00",
    "condition": "partlycloudy",
    "temperature": 22.0,
    "templow": 8.0,
    "precipitation": 1.2,
    "precipitation_probability": 40,
    "apparent_temperature": 16.0,
    "humidity": 72,
    "pressure": 1013.0,
    "cloud_coverage": 60.0,
    "uv_index": 3.0,
    "wind_speed": 14.0,
    "wind_gust_speed": 28.0,
    "wind_bearing": 225,
}]}}

from tests.conftest import assert_no_bleed

@pytest.mark.parametrize("condition", CONDITIONS)
@pytest.mark.parametrize("row_span,col_span", SIZES)
async def test_weather_snapshot(hass, assert_png_snapshot, condition, row_span, col_span):
    hass.states.async_set(
        "weather.home", condition,
        {
            "temperature": 18.5, "temperature_unit": "°C",
            "humidity": 72, "pressure": 1013.0, "pressure_unit": "hPa",
            "wind_speed": 14.0, "wind_speed_unit": "km/h", "wind_bearing": 225,
            "wind_gust_speed": 28.0,
            "cloud_coverage": 60.0, "uv_index": 3.0,
            "apparent_temperature": 16.0,
            "visibility": 12.0, "visibility_unit": "km",
        },
    )
    hass.services.async_register(
        "weather", "get_forecasts", AsyncMock(return_value=DAILY_FORECAST),
        supports_response=SupportsResponse.ONLY,
    )
    widgets = [{"type": "weather", "row": 0, "col": 0,
                "row_span": row_span, "col_span": col_span,
                "config": {"entity_id": "weather.home"}}]
    png = await render_layout(hass, widgets, _coord())
    assert_no_bleed(png, widgets)
    assert_png_snapshot(png, f"weather_{condition}_{row_span}x{col_span}")

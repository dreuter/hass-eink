"""Golden master tests for full multi-widget layouts."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

FIXTURE_IMAGE = Path(__file__).parent / "fixtures" / "atlas_mountains.jpg"
_TODAY = date.today().isoformat()

import pytest

from custom_components.eink.renderer import render_layout


def _coord():
    c = MagicMock()
    c._image_indices = {}
    c._image_lists = {}
    return c


EVENTS = {
    "calendar.test": {
        "events": [
            {"start": f"{_TODAY}T09:00:00+02:00", "end": f"{_TODAY}T10:00:00+02:00", "summary": "Standup"},
            {"start": f"{_TODAY}T14:00:00+02:00", "end": f"{_TODAY}T15:00:00+02:00", "summary": "Review"},
            {"start": _TODAY, "summary": "Holiday"},
        ]
    }
}


from homeassistant.core import SupportsResponse


async def test_weather_and_calendar_snapshot(hass, assert_png_snapshot):
    hass.states.async_set("weather.home", "partlycloudy",
                          {"temperature": 14.0, "temperature_unit": "°C"})
    hass.services.async_register(
        "calendar", "get_events", AsyncMock(return_value=EVENTS),
        supports_response=SupportsResponse.ONLY,
    )
    coord = MagicMock()
    coord._image_indices = {}
    coord._image_lists = {}
    coord.dither = "floyd-steinberg"
    widgets = [
        {"type": "weather",  "row": 0, "col": 0, "row_span": 3, "col_span": 3,
         "config": {"entity_id": "weather.home"}},
        {"type": "calendar", "row": 0, "col": 3, "row_span": 2, "col_span": 1,
         "config": {"entity_id": "calendar.test", "start_hour": 7, "end_hour": 18}},
        {"type": "image",    "row": 2, "col": 3, "row_span": 1, "col_span": 1,
         "config": {"media_content_id": "media-source://media_source/local/test"}},
    ]
    with patch(
        "custom_components.eink.widgets.image._browse",
        AsyncMock(return_value=[str(FIXTURE_IMAGE)]),
    ):
        png = await render_layout(hass, widgets, coord)
    assert_png_snapshot(png, "layout_weather_and_calendar")

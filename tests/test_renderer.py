"""Tests for the grid renderer."""
import io
import pytest
from unittest.mock import AsyncMock, MagicMock

from PIL import Image

from custom_components.eink.renderer import render_layout
from custom_components.eink.const import DISPLAY_WIDTH, DISPLAY_HEIGHT


def _make_coordinator():
    coord = MagicMock()
    coord._image_indices = {}
    coord._image_lists = {}
    coord.dither = "none"
    return coord


async def test_render_empty_layout(hass):
    png = await render_layout(hass, [], _make_coordinator())
    img = Image.open(io.BytesIO(png))
    assert img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)
    assert img.format == "PNG"


async def test_render_weather_widget(hass):
    hass.states.async_set(
        "weather.home",
        "sunny",
        {"temperature": 22, "temperature_unit": "°C"},
    )
    widgets = [{"type": "weather", "row": 0, "col": 0, "row_span": 1, "col_span": 1,
                "config": {"entity_id": "weather.home"}}]
    png = await render_layout(hass, widgets, _make_coordinator())
    img = Image.open(io.BytesIO(png))
    assert img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)


async def test_render_missing_weather_entity(hass):
    """Missing entity should not crash — draws error text instead."""
    widgets = [{"type": "weather", "row": 0, "col": 0, "row_span": 1, "col_span": 1,
                "config": {"entity_id": "weather.nonexistent"}}]
    png = await render_layout(hass, widgets, _make_coordinator())
    assert png[:4] == b"\x89PNG"


async def test_render_calendar_widget(hass):
    from homeassistant.core import SupportsResponse
    hass.services.async_register(
        "calendar", "get_events",
        AsyncMock(return_value={
            "calendar.home": {
                "events": [
                    {"start": "2026-04-13T09:00:00+00:00", "end": "2026-04-13T10:00:00+00:00", "summary": "Team standup"},
                    {"start": "2026-04-13", "summary": "Holiday"},
                ]
            }
        }),
        supports_response=SupportsResponse.ONLY,
    )
    widgets = [{"type": "calendar", "row": 0, "col": 0, "row_span": 3, "col_span": 2,
                "config": {"entity_id": "calendar.home", "start_hour": 8, "end_hour": 18}}]
    png = await render_layout(hass, widgets, _make_coordinator())
    assert png[:4] == b"\x89PNG"

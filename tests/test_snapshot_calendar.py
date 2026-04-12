"""Golden master tests for the calendar widget."""
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


EVENTS = {
    "calendar.test": {
        "events": [
            {"start": "2026-04-12T08:00:00+02:00", "end": "2026-04-12T09:00:00+02:00", "summary": "Morning standup"},
            {"start": "2026-04-12T12:00:00+02:00", "end": "2026-04-12T13:00:00+02:00", "summary": "Lunch"},
            {"start": "2026-04-12T15:00:00+02:00", "end": "2026-04-12T16:30:00+02:00", "summary": "Long meeting"},
            {"start": "2026-04-12", "summary": "All day event"},
        ]
    }
}

EVENTS_MULTI = {
    "calendar.work": {
        "events": [
            {"start": "2026-04-12T09:00:00+02:00", "end": "2026-04-12T10:00:00+02:00", "summary": "Standup"},
            {"start": "2026-04-12T14:00:00+02:00", "end": "2026-04-12T15:00:00+02:00", "summary": "Review"},
        ]
    },
    "calendar.family": {
        "events": [
            {"start": "2026-04-12T09:30:00+02:00", "end": "2026-04-12T10:30:00+02:00", "summary": "Doctor"},
            {"start": "2026-04-12T17:00:00+02:00", "end": "2026-04-12T18:00:00+02:00", "summary": "Dinner"},
        ]
    },
    "calendar.sport": {
        "events": [
            {"start": "2026-04-12T07:00:00+02:00", "end": "2026-04-12T08:00:00+02:00", "summary": "Run"},
        ]
    },
}

FORECAST = [
    {"datetime": f"2026-04-12T{h:02d}:00:00+02:00", "condition": c, "temperature": 15 + h * 0.5, "precipitation": p}
    for h, c, p in [
        (8, "sunny", 0), (9, "partlycloudy", 0), (10, "cloudy", 0.2),
        (11, "rainy", 1.5), (12, "pouring", 3.0), (13, "cloudy", 0.5),
        (14, "partlycloudy", 0), (15, "sunny", 0), (16, "sunny", 0),
        (17, "clear-night", 0),
    ]
]

SIZES = [(3, 1), (3, 2), (3, 4)]


from tests.conftest import assert_no_bleed

@pytest.mark.parametrize("row_span,col_span", SIZES)
async def test_calendar_snapshot(hass, assert_png_snapshot, row_span, col_span):
    hass.services.async_register(
        "calendar", "get_events", AsyncMock(return_value=EVENTS),
        supports_response=SupportsResponse.ONLY,
    )
    widgets = [{"type": "calendar", "row": 0, "col": 0,
                "row_span": row_span, "col_span": col_span,
                "config": {"entity_id": "calendar.test", "start_hour": 7, "end_hour": 18}}]
    png = await render_layout(hass, widgets, _coord())
    assert_no_bleed(png, widgets)
    assert_png_snapshot(png, f"calendar_{row_span}x{col_span}")


@pytest.mark.parametrize("row_span,col_span", SIZES)
async def test_calendar_with_forecast_snapshot(hass, assert_png_snapshot, row_span, col_span):
    hass.services.async_register(
        "calendar", "get_events", AsyncMock(return_value=EVENTS),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        "weather", "get_forecasts",
        AsyncMock(return_value={"weather.forecast": {"forecast": FORECAST}}),
        supports_response=SupportsResponse.ONLY,
    )
    widgets = [{"type": "calendar", "row": 0, "col": 0,
                "row_span": row_span, "col_span": col_span,
                "config": {
                    "entity_id": "calendar.test",
                    "forecast_entity": "weather.forecast",
                    "start_hour": 7, "end_hour": 18,
                }}]
    png = await render_layout(hass, widgets, _coord())
    assert_no_bleed(png, widgets)
    assert_png_snapshot(png, f"calendar_forecast_{row_span}x{col_span}")


async def test_calendar_multi_snapshot(hass, assert_png_snapshot):
    async def _get_events(call):
        entity_id = call.data["entity_id"]
        return {entity_id: EVENTS_MULTI.get(entity_id, {"events": []})}

    hass.services.async_register(
        "calendar", "get_events", _get_events,
        supports_response=SupportsResponse.ONLY,
    )
    widgets = [{"type": "calendar", "row": 0, "col": 0,
                "row_span": 3, "col_span": 2,
                "config": {
                    "calendars": [
                        {"entity_id": "calendar.work",   "color": "blue"},
                        {"entity_id": "calendar.family", "color": "red"},
                        {"entity_id": "calendar.sport",  "color": "green"},
                    ],
                    "start_hour": 7, "end_hour": 18,
                }}]
    png = await render_layout(hass, widgets, _coord())
    assert_png_snapshot(png, "calendar_multi_3x2")

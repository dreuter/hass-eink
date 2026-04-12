"""Grid renderer — turns a widget list into a PNG bytes object."""
from __future__ import annotations

import io
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from .const import DISPLAY_HEIGHT, DISPLAY_WIDTH, GRID_COLS, GRID_ROWS, WIDGET_CALENDAR, WIDGET_IMAGE, WIDGET_WEATHER

if TYPE_CHECKING:
    from .coordinator import DisplayCoordinator


def _cell_bbox(row: int, col: int, row_span: int, col_span: int) -> tuple[int, int, int, int]:
    cell_w = DISPLAY_WIDTH // GRID_COLS
    cell_h = DISPLAY_HEIGHT // GRID_ROWS
    x0 = col * cell_w
    y0 = row * cell_h
    x1 = x0 + col_span * cell_w
    y1 = y0 + row_span * cell_h
    return x0, y0, x1, y1


async def render_layout(
    hass: HomeAssistant,
    widgets: list[dict],
    coordinator: "DisplayCoordinator",
) -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    for idx, widget in enumerate(widgets):
        bbox = _cell_bbox(
            widget.get("row", 0),
            widget.get("col", 0),
            widget.get("row_span", 1),
            widget.get("col_span", 1),
        )
        wtype = widget.get("type")
        cfg = widget.get("config", {})

        try:
            if wtype == WIDGET_WEATHER:
                from .widgets.weather import render_weather
                await render_weather(hass, img, draw, bbox, cfg)
            elif wtype == WIDGET_CALENDAR:
                from .widgets.calendar import render_calendar
                await render_calendar(hass, img, draw, bbox, cfg)
            elif wtype == WIDGET_IMAGE:
                from .widgets.image import render_image
                await render_image(hass, img, draw, bbox, cfg, coordinator, idx)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Widget %s render failed", wtype)
            draw.rectangle(bbox, outline="red")

        # draw cell border (inset 1px so outline stays within bbox)
        draw.rectangle((bbox[0], bbox[1], bbox[2]-1, bbox[3]-1), outline="lightgray")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

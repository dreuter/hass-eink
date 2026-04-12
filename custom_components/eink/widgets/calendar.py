"""Calendar widget — day view with hour timeline, event bubbles, and optional hourly forecast."""
from __future__ import annotations

from datetime import datetime, timedelta

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from homeassistant.core import HomeAssistant

_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_ICONS_DIR = Path(__file__).parent.parent / "icons"


def _load_icon(condition: str, size: int) -> Image.Image | None:
    path = _ICONS_DIR / f"{condition}.png"
    if not path.exists():
        return None
    return Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)


def _fonts(size: int):
    try:
        return (
            ImageFont.truetype(_FONT, size),
            ImageFont.truetype(_FONT_BOLD, size),
        )
    except OSError:
        f = ImageFont.load_default()
        return f, f


async def _get_forecast(hass: HomeAssistant, entity_id: str, start_hour: int, end_hour: int) -> dict[int, dict]:
    """Return {hour: forecast_entry} for today's hours in range."""
    try:
        result = await hass.services.async_call(
            "weather", "get_forecasts",
            {"entity_id": entity_id, "type": "hourly"},
            blocking=True, return_response=True,
        )
        forecasts = (result or {}).get(entity_id, {}).get("forecast", [])
    except Exception:
        return {}

    today = datetime.now().astimezone().date()
    by_hour = {}
    for f in forecasts:
        try:
            dt = datetime.fromisoformat(f["datetime"]).astimezone()
            if dt.date() == today and start_hour <= dt.hour < end_hour:
                by_hour[dt.hour] = f
        except (KeyError, ValueError):
            pass
    return by_hour


async def render_calendar(
    hass: HomeAssistant,
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    cfg: dict,
) -> None:
    entity_id = cfg.get("entity_id", "calendar.home")
    start_hour = int(cfg.get("start_hour") or 0)
    end_hour = int(cfg.get("end_hour") or 24)
    forecast_entity = cfg.get("forecast_entity")
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0

    font_sm, font_bold = _fonts(max(9, h // 20))

    # Fetch events
    local_now = datetime.now().astimezone()
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    try:
        result = await hass.services.async_call(
            "calendar", "get_events",
            {
                "entity_id": entity_id,
                "start_date_time": day_start.isoformat(),
                "end_date_time": day_end.isoformat(),
            },
            blocking=True, return_response=True,
        )
        events = (result or {}).get(entity_id, {}).get("events", [])
    except Exception:
        draw.text((x0 + 4, y0 + 4), "Calendar error", fill="red", font=font_sm)
        return

    # Fetch forecast if configured
    forecast = await _get_forecast(hass, forecast_entity, start_hour, end_hour) if forecast_entity else {}

    # All-day banner
    all_day = [e for e in events if "T" not in e.get("start", "")]
    timed   = [e for e in events if "T" in e.get("start", "")]

    banner_h = (font_sm.size + 4) * len(all_day) if all_day else 0
    if all_day:
        draw.rectangle((x0, y0, x1 - 1, y0 + banner_h), fill="black")
        for i, e in enumerate(all_day):
            draw.text((x0 + 4, y0 + i * (font_sm.size + 4) + 2), e.get("summary", ""), font=font_sm, fill="white")

    # Timeline
    tl_y0 = y0 + banner_h
    tl_h = y1 - tl_y0
    hour_range = end_hour - start_hour
    label_w = 28
    forecast_w = 52 if forecast else 0
    event_x0 = x0 + label_w + forecast_w + 2
    event_x1 = x1 - 2

    def time_to_y(hour: float) -> int:
        return int(tl_y0 + (hour - start_hour) / hour_range * tl_h)

    # Hour lines + labels + forecast
    for hr in range(start_hour, end_hour + 1):
        y = time_to_y(hr)
        draw.line((x0 + label_w, y, x1 - 1, y), fill="lightgray", width=1)
        if hr < end_hour:
            draw.text((x0 + 2, y + 1), f"{hr:02d}", font=font_sm, fill="gray")

            if forecast and hr in forecast:
                f = forecast[hr]
                condition = f.get("condition", "")
                temp = f.get("temperature")
                precip = f.get("precipitation") or 0
                icon_size = font_sm.size + 2
                col_x = x0 + label_w  # left edge of forecast column
                fy = y + 1
                icon = await hass.async_add_executor_job(_load_icon, condition, icon_size)
                if icon:
                    img.paste(icon, (col_x + 2, fy), icon)
                tx = col_x + icon_size + 4
                if temp is not None:
                    draw.text((tx, fy), f"{temp:.0f}°", font=font_sm, fill="black")
                if precip > 0:
                    draw.text((tx, fy + font_sm.size + 1), f"{precip:.1f}mm", font=font_sm, fill="#0066cc")

    # Event bubbles
    for event in timed:
        try:
            ev_start = datetime.fromisoformat(event["start"]).astimezone()
            ev_end   = datetime.fromisoformat(event.get("end", event["start"])).astimezone()
        except (KeyError, ValueError):
            continue

        sh = max(ev_start.hour + ev_start.minute / 60, start_hour)
        eh = min(ev_end.hour + ev_end.minute / 60, end_hour)
        if sh >= eh:
            continue

        ey0 = time_to_y(sh) + 1
        ey1 = max(time_to_y(eh) - 1, ey0 + font_sm.size + 2)
        draw.rounded_rectangle((event_x0, ey0, event_x1, ey1), radius=2, fill="black")
        draw.text(
            (event_x0 + 2, ey0 + 1),
            f"{ev_start.strftime('%H:%M')} {event.get('summary', '')}",
            font=font_sm, fill="white",
        )

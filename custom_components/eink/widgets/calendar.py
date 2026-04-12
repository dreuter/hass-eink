"""Calendar widget — day view with hour timeline and event bubbles."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageFont
from homeassistant.core import HomeAssistant

_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _fonts(size: int):
    try:
        return (
            ImageFont.truetype(_FONT, size),
            ImageFont.truetype(_FONT_BOLD, size),
        )
    except OSError:
        f = ImageFont.load_default()
        return f, f


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
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0

    font_sm, font_bold = _fonts(max(9, h // 20))

    # Fetch today's events
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

    # Split all-day vs timed
    all_day = [e for e in events if "T" not in e.get("start", "")]
    timed   = [e for e in events if "T" in e.get("start", "")]

    # --- All-day banner ---
    banner_h = (font_sm.size + 4) * len(all_day) if all_day else 0
    if all_day:
        draw.rectangle((x0, y0, x1, y0 + banner_h), fill="black")
        for i, e in enumerate(all_day):
            draw.text(
                (x0 + 4, y0 + i * (font_sm.size + 4) + 2),
                e.get("summary", ""),
                font=font_sm, fill="white",
            )

    # --- Timeline area ---
    tl_y0 = y0 + banner_h
    tl_y1 = y1
    tl_h = tl_y1 - tl_y0
    hour_range = end_hour - start_hour
    label_w = 28  # px reserved for hour labels

    def time_to_y(hour: float) -> int:
        frac = (hour - start_hour) / hour_range
        return int(tl_y0 + frac * tl_h)

    # Hour lines + labels
    for hr in range(start_hour, end_hour + 1):
        y = time_to_y(hr)
        draw.line((x0 + label_w, y, x1, y), fill="lightgray", width=1)
        if hr < end_hour:
            draw.text((x0 + 2, y + 1), f"{hr:02d}", font=font_sm, fill="gray")

    # Current time indicator
    now_hour = local_now.hour + local_now.minute / 60
    if start_hour <= now_hour <= end_hour:
        ny = time_to_y(now_hour)
        draw.line((x0 + label_w, ny, x1, ny), fill="red", width=2)

    # Event bubbles
    event_x0 = x0 + label_w + 2
    event_x1 = x1 - 2
    for event in timed:
        try:
            ev_start = datetime.fromisoformat(event["start"]).astimezone()
            ev_end   = datetime.fromisoformat(event.get("end", event["start"])).astimezone()
        except (KeyError, ValueError):
            continue

        sh = ev_start.hour + ev_start.minute / 60
        eh = ev_end.hour + ev_end.minute / 60
        sh = max(sh, start_hour)
        eh = min(eh, end_hour)
        if sh >= eh:
            continue

        ey0 = time_to_y(sh) + 1
        ey1 = max(time_to_y(eh) - 1, ey0 + font_sm.size + 4)

        draw.rounded_rectangle((event_x0, ey0, event_x1, ey1), radius=3, fill="black")
        draw.text(
            (event_x0 + 3, ey0 + 2),
            f"{ev_start.strftime('%H:%M')} {event.get('summary', '')}",
            font=font_sm, fill="white",
        )

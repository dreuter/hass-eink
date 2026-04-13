"""Calendar widget — day view with hour timeline, event bubbles, and optional hourly forecast."""
from __future__ import annotations

from datetime import datetime, timedelta

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from homeassistant.core import HomeAssistant
from ..const import BLACK, WHITE, RED, BLUE, GREEN, YELLOW

def _draw_gray_line(draw, x0: int, y: int, x1: int) -> None:
    for x in range(x0, x1):
        if (x + y) % 2 == 0:
            draw.point((x, y), fill=BLACK)

_FONTS_DIR = Path(__file__).parent.parent / "fonts"
_FONT = _FONTS_DIR / "DejaVuSans.ttf"
_FONT_BOLD = _FONTS_DIR / "DejaVuSans-Bold.ttf"
_ICONS_DIR = Path(__file__).parent.parent / "icons"

# Named palette colors for calendar config
_COLOR_MAP = {
    "black":  BLACK,
    "white":  WHITE,
    "yellow": YELLOW,
    "red":    RED,
    "blue":   BLUE,
    "green":  GREEN,
}
_DEFAULT_COLORS = [BLACK, BLUE, GREEN, RED, YELLOW]


def _load_icon(condition: str, size: int, icon_set: str = "weather-icons") -> Image.Image | None:
    path = _ICONS_DIR / icon_set / f"{condition}.png"
    if not path.exists():
        return None
    return Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)


def _fonts(size: int):
    return (
        ImageFont.truetype(str(_FONT), size),
        ImageFont.truetype(str(_FONT_BOLD), size),
    )


async def _get_events(hass: HomeAssistant, entity_id: str, day_start: datetime, day_end: datetime) -> list[dict]:
    try:
        result = await hass.services.async_call(
            "calendar", "get_events",
            {"entity_id": entity_id,
             "start_date_time": day_start.isoformat(),
             "end_date_time": day_end.isoformat()},
            blocking=True, return_response=True,
        )
        return (result or {}).get(entity_id, {}).get("events", [])
    except Exception:
        return []


async def _get_forecast(hass: HomeAssistant, entity_id: str, start_hour: int, end_hour: int) -> dict[int, dict]:
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
    dither: str = "none",
) -> None:
    start_hour = int(cfg.get("start_hour") or 0)
    end_hour = int(cfg.get("end_hour") or 24)
    forecast_entity = cfg.get("forecast_entity")
    icon_set = cfg.get("icon_set", "weather-icons")
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0

    font_sm, font_bold = _fonts(max(9, h // 20))

    # Resolve calendar list — support legacy single entity_id
    calendars_cfg = cfg.get("calendars")
    if not calendars_cfg:
        entity_id = cfg.get("entity_id", "calendar.home")
        calendars_cfg = [{"entity_id": entity_id}]

    # Assign colors
    calendars = []
    for i, cal in enumerate(calendars_cfg):
        if not cal.get("entity_id"):
            continue
        color_name = cal.get("color")
        color = _COLOR_MAP.get(color_name) if color_name else _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)]
        calendars.append((cal["entity_id"], color))

    local_now = datetime.now().astimezone()
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    # Fetch all events
    all_events: list[tuple[dict, tuple]] = []
    for entity_id, color in calendars:
        for event in await _get_events(hass, entity_id, day_start, day_end):
            all_events.append((event, color))

    if not all_events and not calendars:
        draw.text((x0 + 4, y0 + 4), "Calendar error", fill=RED, font=font_sm)
        return

    forecast = await _get_forecast(hass, forecast_entity, start_hour, end_hour) if forecast_entity else {}

    all_day = [(e, c) for e, c in all_events if "T" not in e.get("start", "")]
    timed   = [(e, c) for e, c in all_events if "T" in e.get("start", "")]

    banner_h = (font_sm.size + 4) * len(all_day) if all_day else 0
    if all_day:
        draw.rectangle((x0, y0, x1 - 1, y0 + banner_h), fill=BLACK)
        for i, (e, c) in enumerate(all_day):
            draw.text((x0 + 4, y0 + i * (font_sm.size + 4) + 2), e.get("summary", ""), font=font_sm, fill=WHITE)

    tl_y0 = y0 + banner_h
    tl_h = y1 - tl_y0
    hour_range = end_hour - start_hour
    label_w = 28
    forecast_w = 72 if forecast else 4
    event_x0 = x0 + label_w + forecast_w + 2
    event_x1 = x1 - 2

    def time_to_y(hour: float) -> int:
        return int(tl_y0 + (hour - start_hour) / hour_range * tl_h)

    for hr in range(start_hour, end_hour + 1):
        y = time_to_y(hr)
        _draw_gray_line(draw, x0 + label_w, y, x1 - 1)
        if hr < end_hour:
            draw.text((x0 + 2, y + 1), f"{hr:02d}", font=font_sm, fill=BLACK)

            if forecast and hr in forecast:
                f = forecast[hr]
                condition = f.get("condition", "")
                temp = f.get("temperature")
                precip = f.get("precipitation") or 0
                font_fc = _fonts(max(8, font_sm.size // 2))[0]
                icon_size = font_fc.size * 2
                col_x = x0 + label_w
                fy = y + 1
                icon = await hass.async_add_executor_job(_load_icon, condition, icon_size, icon_set)
                if icon:
                    if dither != "none":
                        from ..dither import dither_image
                        bg = Image.new("RGB", icon.size, WHITE)
                        bg.paste(icon, mask=icon.split()[3])
                        bg = await hass.async_add_executor_job(dither_image, bg, dither)
                        img.paste(bg, (col_x + 2, fy))
                    else:
                        img.paste(icon, (col_x + 2, fy), icon)
                tx = col_x + icon_size + 4
                if temp is not None and precip > 0:
                    draw.text((tx, fy), f"{temp:.0f}°", font=font_fc, fill=BLACK)
                    draw.text((tx, fy + font_fc.size + 1), f"{precip:.1f}mm", font=font_fc, fill=BLUE)
                elif temp is not None:
                    font_fc2 = _fonts(max(8, font_sm.size // 1))[0]
                    draw.text((tx, fy), f"{temp:.0f}°", font=font_fc2, fill=BLACK)

    # Build list of (sh, eh, event, color) and assign columns for overlaps
    slots = []
    for event, color in timed:
        try:
            ev_start = datetime.fromisoformat(event["start"]).astimezone()
            ev_end   = datetime.fromisoformat(event.get("end", event["start"])).astimezone()
        except (KeyError, ValueError):
            continue
        sh = max(ev_start.hour + ev_start.minute / 60, start_hour)
        eh = min(ev_end.hour + ev_end.minute / 60, end_hour)
        if sh >= eh:
            continue
        slots.append([sh, eh, event, color, ev_start, 0, 1])  # col, total_cols appended below

    # Assign columns: greedy interval graph coloring
    for i, s in enumerate(slots):
        used = {s2[5] for s2 in slots[:i] if s2[0] < s[1] and s2[1] > s[0]}
        s[5] = next(c for c in range(len(slots)) if c not in used)
    for i, s in enumerate(slots):
        s[6] = max(s2[5] + 1 for s2 in slots if s2[0] < s[1] and s2[1] > s[0])

    total_w = event_x1 - event_x0
    for sh, eh, event, color, ev_start, col, total_cols in slots:
        col_w = total_w // total_cols
        ex0 = event_x0 + col * col_w
        ex1 = event_x0 + (col + 1) * col_w - 1
        ey0 = time_to_y(sh) + 1
        ey1 = max(time_to_y(eh) - 1, ey0 + font_sm.size + 2)
        draw.rounded_rectangle((ex0, ey0, ex1, ey1), radius=2, fill=color)
        text_color = BLACK if color in (WHITE, YELLOW) else WHITE
        draw.text(
            (ex0 + 2, ey0 + 1),
            event.get("summary", ""),
            font=font_sm, fill=text_color,
        )

"""Weather widget."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, BLACK, WHITE, RED

_ICONS_DIR = Path(__file__).parent.parent / "icons"
_FONTS_DIR = Path(__file__).parent.parent / "fonts"


def _find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(_FONTS_DIR / name), max(8, size))


def _load_icon(condition: str, size: int, icon_set: str = "weather-icons") -> Image.Image | None:
    path = _ICONS_DIR / icon_set / f"{condition}.png"
    if not path.exists():
        return None
    return Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)


async def _condition_label(hass: HomeAssistant, condition: str) -> str:
    from homeassistant.helpers.translation import async_get_translations
    translations = await async_get_translations(hass, hass.config.language, "state", {DOMAIN})
    key = f"component.{DOMAIN}.state.weather.{condition}"
    return translations.get(key, condition.replace("-", " "))


def _wind_arrow(bearing: float) -> str:
    arrows = ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘"]
    return arrows[round(((bearing + 180) % 360) / 45) % 8]


@dataclass
class WeatherData:
    condition: str
    label: str
    temp: Optional[float] = None
    unit: str = "°C"
    apparent: Optional[float] = None
    t_high: Optional[float] = None
    t_low: Optional[float] = None
    wind: Optional[float] = None
    wind_unit: str = "km/h"
    wind_bearing: Optional[float] = None
    wind_gust: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    pressure_unit: str = "hPa"
    cloud: Optional[float] = None
    uv: Optional[float] = None
    visibility: Optional[float] = None
    visibility_unit: str = "km"
    precip_prob: Optional[float] = None
    precip: Optional[float] = None
    forecast_datetime: Optional[str] = None

    def date_str(self) -> Optional[str]:
        if not self.forecast_datetime:
            return None
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(self.forecast_datetime)
            return dt.strftime("%A, %b %-d")
        except ValueError:
            return None

    def temp_str(self) -> Optional[str]:
        return f"{self.temp:.0f}{self.unit}" if self.temp is not None else None

    def feels_like_str(self) -> Optional[str]:
        return f"feels like {self.apparent:.0f}{self.unit}" if self.apparent is not None else None

    def high_low_str(self) -> Optional[str]:
        if self.t_high is not None and self.t_low is not None:
            return f"↓{self.t_low:.0f}°  ↑{self.t_high:.0f}°"
        return None

    def extra_stats(self) -> list[str]:
        stats = []
        if self.wind is not None:
            arrow = _wind_arrow(self.wind_bearing) if self.wind_bearing is not None else ""
            gust_str = f" max {self.wind_gust:.0f}" if self.wind_gust else ""
            stats.append(f"{arrow} {self.wind:.0f}{gust_str} {self.wind_unit}")
        if self.humidity is not None:
            stats.append(f"≋ {self.humidity:.0f}% humidity")
        if self.pressure is not None:
            stats.append(f"⊕ {self.pressure:.0f} {self.pressure_unit}")
        if self.cloud is not None:
            stats.append(f"☁ {self.cloud:.0f}% cloud cover")
        if self.uv is not None:
            stats.append(f"☀ UV {self.uv:.0f}")
        if self.visibility is not None:
            stats.append(f"◎ {self.visibility:.0f} {self.visibility_unit} visibility")
        if self.precip_prob is not None or self.precip is not None:
            parts = []
            if self.precip_prob is not None:
                parts.append(f"{self.precip_prob:.0f}%")
            if self.precip is not None:
                parts.append(f"{self.precip:.1f} mm")
            stats.append(f"☔ {' / '.join(parts)}")
        return stats


async def _fetch_weather_data(hass: HomeAssistant, entity_id: str) -> WeatherData | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    a = state.attributes
    label = await _condition_label(hass, state.state)

    today: dict = {}
    try:
        result = await hass.services.async_call(
            "weather", "get_forecasts",
            {"entity_id": entity_id, "type": "daily"},
            blocking=True, return_response=True,
        )
        forecasts = (result or {}).get(entity_id, {}).get("forecast", [])
        if forecasts:
            today = forecasts[0]
    except Exception:
        pass

    return WeatherData(
        condition=state.state,
        label=label,
        temp=a.get("temperature"),
        unit=a.get("temperature_unit", "°C"),
        apparent=a.get("apparent_temperature") or today.get("apparent_temperature"),
        t_high=today.get("temperature"),
        t_low=today.get("templow"),
        wind=today.get("wind_speed") or a.get("wind_speed"),
        wind_unit=a.get("wind_speed_unit", "km/h"),
        wind_bearing=today.get("wind_bearing") or a.get("wind_bearing"),
        wind_gust=today.get("wind_gust_speed") or a.get("wind_gust_speed"),
        humidity=today.get("humidity") or a.get("humidity"),
        pressure=today.get("pressure") or a.get("pressure"),
        pressure_unit=a.get("pressure_unit", "hPa"),
        cloud=today.get("cloud_coverage") or a.get("cloud_coverage"),
        uv=today.get("uv_index") or a.get("uv_index"),
        visibility=a.get("visibility"),
        visibility_unit=a.get("visibility_unit", "km"),
        precip_prob=today.get("precipitation_probability"),
        precip=today.get("precipitation"),
        forecast_datetime=today.get("datetime"),
    )


async def _paste_icon(
    hass: HomeAssistant,
    img: Image.Image,
    icon: Image.Image,
    pos: tuple[int, int],
    dither: str,
) -> None:
    if dither != "none":
        from ..dither import dither_image
        bg = Image.new("RGB", icon.size, WHITE)
        bg.paste(icon, mask=icon.split()[3])
        bg = await hass.async_add_executor_job(dither_image, bg, dither)
        img.paste(bg, pos)
    else:
        img.paste(icon, pos, icon)


async def _render_small(
    hass: HomeAssistant,
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    data: WeatherData,
    icon_set: str,
    dither: str,
) -> None:
    """1×1 cell: icon top, temp + high/low below."""
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    font_lg = _find_font(min(h // 4, w // 3, 56), bold=True)
    font_md = _find_font(min(h // 7, w // 6, 28), bold=True)

    icon_size = min(w - 16, h - font_lg.size - font_md.size - 18)
    icon = await hass.async_add_executor_job(_load_icon, data.condition, icon_size, icon_set)
    if icon:
        await _paste_icon(hass, img, icon, (x0 + (w - icon_size) // 2, y0 + 4), dither)

    cy = y0 + 4 + icon_size + 4
    if (t := data.temp_str()):
        draw.text((x0 + (w - draw.textlength(t, font=font_lg)) // 2, cy), t, font=font_lg, fill=BLACK)
        cy += font_lg.size + 2
    if (hl := data.high_low_str()):
        draw.text((x0 + (w - draw.textlength(hl, font=font_md)) // 2, cy), hl, font=font_md, fill=BLACK)


async def _render_default(
    hass: HomeAssistant,
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    data: WeatherData,
    icon_set: str,
    dither: str,
) -> None:
    """Medium size: centered icon, condition label, temp stack, stats grid."""
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    font_lg = _find_font(min(h // 4, w // 3, 56), bold=True)
    font_md = _find_font(min(h // 7, w // 6, 28), bold=True)
    font_sm = _find_font(min(h // 9, w // 8, 18))

    icon_size = min(int(w * 0.5), int(h * 0.35))
    icon = await hass.async_add_executor_job(_load_icon, data.condition, icon_size, icon_set)
    if icon:
        await _paste_icon(hass, img, icon, (x0 + (w - icon_size) // 2, y0 + 4), dither)

    cy = y0 + 4 + icon_size + 4

    def center(text: str, font: ImageFont.FreeTypeFont) -> int:
        draw.text((x0 + (w - draw.textlength(text, font=font)) // 2, cy), text, font=font, fill=BLACK)
        return cy + font.size + 4

    cy = center(data.label, font_sm)
    if (t := data.temp_str()):
        cy = center(t, font_lg)
    if (fl := data.feels_like_str()):
        cy = center(fl, font_sm)
    if (hl := data.high_low_str()):
        cy = center(hl, font_md)

    stats = data.extra_stats()
    if not stats:
        return
    cols = 2 if w >= 300 else 1
    col_w = w // cols
    line_h = font_sm.size + 5
    for i, stat in enumerate(stats[:((y1 - cy - 4) // line_h) * cols]):
        draw.text((x0 + (i % cols) * col_w + 8, cy + (i // cols) * line_h), stat, font=font_sm, fill=BLACK)


async def _render_large(
    hass: HomeAssistant,
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    data: WeatherData,
    icon_set: str,
    dither: str,
) -> None:
    """Large (≥3×2): draw stats bottom-up, condition label above them, icon fills rest.

    Left column:  temp, feels like, high/low
    Right column: wind, humidity, pressure, etc.
    """
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    col_w = w // 2
    pad_x = 16
    pad_y = 4

    font_lg = _find_font(min(h // 4, (col_w - pad_x) // 2, 64), bold=True)
    font_md = _find_font(min(h // 7, (col_w - pad_x) // 3, 32), bold=True)
    font_fl = _find_font(min(h // 7, (col_w - pad_x) // 5, 24))
    font_sm = _find_font(min(h // 9, w // 8, 18))

    left: list[tuple[str, ImageFont.FreeTypeFont]] = []
    if (t := data.temp_str()):
        left.append((t, font_lg))
    if (fl := data.feels_like_str()):
        left.append((fl, font_fl))
    if (hl := data.high_low_str()):
        left.append((hl, font_md))

    right: list[tuple[str, ImageFont.FreeTypeFont]] = [
        (s, font_sm) for s in filter(None, [data.date_str(), *data.extra_stats()])
    ]

    def col_h(items: list[tuple[str, ImageFont.FreeTypeFont]]) -> int:
        return sum(f.size + pad_y for _, f in items)

    # Move items from right to left until columns are balanced
    while right and col_h(right) > col_h(left) + right[-1][1].size + pad_y:
        left.append(right.pop())

    # Place stats section: anchor top of taller column, shifted up 8px from bottom
    stats_h = max(col_h(left), col_h(right))
    stats_top = y1 - stats_h - 8

    # Draw columns top-down
    ly = stats_top
    for text, font in left:
        draw.text((x0 + pad_x, ly), text, font=font, fill=BLACK)
        ly += font.size + pad_y

    ry = stats_top
    for text, font in right:
        draw.text((x0 + col_w, ry), text, font=font, fill=BLACK)
        ry += font.size + pad_y

    # Condition label just above the stats
    label_y = stats_top - font_sm.size - pad_y
    draw.text((x0 + (w - draw.textlength(data.label, font=font_sm)) // 2, label_y), data.label, font=font_sm, fill=BLACK)

    # Icon fills remaining space above label
    icon_size = max(label_y - y0 - 8, 32)
    icon = await hass.async_add_executor_job(_load_icon, data.condition, icon_size, icon_set)
    if icon:
        await _paste_icon(hass, img, icon, (x0 + (w - icon_size) // 2, y0 + 4), dither)



async def render_weather(
    hass: HomeAssistant,
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    cfg: dict,
    dither: str = "none",
) -> None:
    entity_id = cfg.get("entity_id", "weather.forecast_home")
    icon_set = cfg.get("icon_set", "weather-icons")
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0

    data = await _fetch_weather_data(hass, entity_id)
    if data is None:
        draw.text((x0 + 4, y0 + 4), f"No entity:\n{entity_id}", fill=RED)
        return

    small = w <= 200 and h <= 200
    large = w >= 400 and h >= 320

    if small:
        await _render_small(hass, img, draw, bbox, data, icon_set, dither)
    elif large:
        await _render_large(hass, img, draw, bbox, data, icon_set, dither)
    else:
        await _render_default(hass, img, draw, bbox, data, icon_set, dither)

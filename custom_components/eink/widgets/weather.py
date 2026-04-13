"""Weather widget."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, BLACK, WHITE, RED, BLUE

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
    state = hass.states.get(entity_id)
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0

    if state is None:
        draw.text((x0 + 4, y0 + 4), f"No entity:\n{entity_id}", fill=RED)
        return

    a = state.attributes
    condition = state.state
    temp = a.get("temperature")
    unit = a.get("temperature_unit", "°C")
    label = await _condition_label(hass, condition)
    small = (w <= 200 and h <= 200)

    # Fetch daily forecast for high/low and extra stats
    today = {}
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

    font_lg = _find_font(min(h // 4, w // 3, 56), bold=True)
    font_md = _find_font(min(h // 7, w // 6, 28), bold=True)
    font_sm = _find_font(min(h // 9, w // 8, 18))

    # For 1x1: reserve space for icon + temp + high/low
    if small:
        hl_h = font_md.size + 4
        temp_h = font_lg.size + 2
        icon_size = min(w - 16, h - temp_h - hl_h - 12)
    else:
        icon_size = min(int(w * 0.5), int(h * 0.35))
    icon = await hass.async_add_executor_job(_load_icon, condition, icon_size, icon_set)
    ix = x0 + (w - icon_size) // 2
    iy = y0 + 4
    if icon:
        if dither != "none":
            from ..dither import dither_image
            bg = Image.new("RGB", icon.size, WHITE)
            bg.paste(icon, mask=icon.split()[3])
            bg = await hass.async_add_executor_job(dither_image, bg, dither)
            img.paste(bg, (ix, iy))
        else:
            img.paste(icon, (ix, iy), icon)

    cy = iy + icon_size + 4

    # --- Condition label ---
    if not small:
        draw.text((x0 + (w - draw.textlength(label, font=font_sm)) // 2, cy), label, font=font_sm, fill=BLACK)
        cy += font_sm.size + 4

    # --- Current temp ---
    if temp is not None:
        t_str = f"{temp:.0f}{unit}"
        tw = draw.textlength(t_str, font=font_lg)
        draw.text((x0 + (w - tw) // 2, cy), t_str, font=font_lg, fill=BLACK)
        cy += font_lg.size + 2

    # --- Feels like ---
    apparent = a.get("apparent_temperature") or today.get("apparent_temperature")
    if apparent is not None and not small:
        fl = f"feels like {apparent:.0f}{unit}"
        draw.text((x0 + (w - draw.textlength(fl, font=font_sm)) // 2, cy), fl, font=font_sm, fill=BLACK)
        cy += font_sm.size + 2

    # --- High / Low ---
    t_high = today.get("temperature")
    t_low = today.get("templow")
    if t_high is not None and t_low is not None:
        hl = f"↓{t_low:.0f}°  ↑{t_high:.0f}°"
        draw.text((x0 + (w - draw.textlength(hl, font=font_md)) // 2, cy), hl, font=font_md, fill=BLACK)
        cy += font_md.size + 6

    if small:
        return

    # --- Stats grid ---
    stats = []
    wind = today.get("wind_speed") or a.get("wind_speed")
    bearing = today.get("wind_bearing") or a.get("wind_bearing")
    wind_unit = a.get("wind_speed_unit", "km/h")
    gust = today.get("wind_gust_speed") or a.get("wind_gust_speed")
    if wind is not None:
        arrow = _wind_arrow(bearing) if bearing is not None else ""
        gust_str = f" max {gust:.0f}" if gust else ""
        stats.append(f"{arrow} {wind:.0f}{gust_str} {wind_unit}")

    humidity = today.get("humidity") or a.get("humidity")
    if humidity is not None:
        stats.append(f"≋ {humidity:.0f}% humidity")

    pressure = today.get("pressure") or a.get("pressure")
    if pressure is not None:
        stats.append(f"⊕ {pressure:.0f} {a.get('pressure_unit', 'hPa')}")

    cloud = today.get("cloud_coverage") or a.get("cloud_coverage")
    if cloud is not None:
        stats.append(f"☁ {cloud:.0f}% cloud cover")

    uv = today.get("uv_index") or a.get("uv_index")
    if uv is not None:
        stats.append(f"☀ UV {uv:.0f}")

    visibility = a.get("visibility")
    if visibility is not None:
        stats.append(f"◎ {visibility:.0f} {a.get('visibility_unit', 'km')} visibility")

    precip_prob = today.get("precipitation_probability")
    precip = today.get("precipitation")
    if precip_prob is not None or precip is not None:
        parts = []
        if precip_prob is not None:
            parts.append(f"{precip_prob:.0f}%")
        if precip is not None:
            parts.append(f"{precip:.1f} mm")
        stats.append(f"☔ {' / '.join(parts)}")

    if not stats:
        return

    # Two-column grid at the bottom
    cols = 2 if w >= 300 else 1
    col_w = w // cols
    line_h = font_sm.size + 5
    for i, stat in enumerate(stats[:((y1 - cy - 4) // line_h) * cols]):
        col = i % cols
        row = i // cols
        draw.text((x0 + col * col_w + 8, cy + row * line_h), stat, font=font_sm, fill=BLACK)

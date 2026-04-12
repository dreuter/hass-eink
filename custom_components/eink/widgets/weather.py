"""Weather widget."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont
from homeassistant.core import HomeAssistant

# Map HA weather condition strings to simple emoji-like text symbols
CONDITION_ICONS = {
    "clear-night": "🌙",
    "cloudy": "☁️",
    "exceptional": "⚠️",
    "fog": "🌫️",
    "hail": "🌨️",
    "lightning": "⚡",
    "lightning-rainy": "⛈️",
    "partlycloudy": "⛅",
    "pouring": "🌧️",
    "rainy": "🌦️",
    "snowy": "❄️",
    "snowy-rainy": "🌨️",
    "sunny": "☀️",
    "windy": "💨",
    "windy-variant": "💨",
}


async def render_weather(
    hass: HomeAssistant,
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    cfg: dict,
) -> None:
    entity_id = cfg.get("entity_id", "weather.home")
    state = hass.states.get(entity_id)
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0

    if state is None:
        draw.text((x0 + 4, y0 + 4), f"No entity:\n{entity_id}", fill="red")
        return

    condition = state.state
    icon = CONDITION_ICONS.get(condition, "?")
    temp = state.attributes.get("temperature", "")
    unit = state.attributes.get("temperature_unit", "°C")

    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", min(h // 2, 80))
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", min(h // 4, 32))
    except OSError:
        font_large = ImageFont.load_default()
        font_small = font_large

    # condition text (icon fallback as text)
    draw.text((x0 + 8, y0 + 8), icon, font=font_large, fill="black")
    draw.text((x0 + 8, y0 + h // 2 + 4), f"{temp}{unit}", font=font_small, fill="black")
    draw.text((x0 + 8, y0 + h * 3 // 4), condition.replace("-", " ").title(), font=font_small, fill="gray")

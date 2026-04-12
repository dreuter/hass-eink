"""Weather widget."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from homeassistant.core import HomeAssistant

from ..const import DOMAIN

_ICONS_DIR = Path(__file__).parent.parent / "icons"


def _load_icon(condition: str, size: int) -> Image.Image | None:
    path = _ICONS_DIR / f"{condition}.png"
    if not path.exists():
        return None
    return Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)


async def _condition_label(hass: HomeAssistant, condition: str) -> str:
    from homeassistant.helpers.translation import async_get_translations
    translations = await async_get_translations(
        hass, hass.config.language, "state", {DOMAIN}
    )
    key = f"component.{DOMAIN}.state.weather.{condition}"
    return translations.get(key, condition.replace("-", " "))


async def render_weather(
    hass: HomeAssistant,
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    cfg: dict,
) -> None:
    entity_id = cfg.get("entity_id", "weather.forecast_home")
    state = hass.states.get(entity_id)
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0

    if state is None:
        draw.text((x0 + 4, y0 + 4), f"No entity:\n{entity_id}", fill="red")
        return

    condition = state.state
    temp = state.attributes.get("temperature", "")
    unit = state.attributes.get("temperature_unit", "°C")
    label = await _condition_label(hass, condition)

    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", min(h // 3, w // 5, 64))
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", min(h // 5, w // 8, 32))
    except OSError:
        font_large = ImageFont.load_default()
        font_small = font_large

    icon_size = min(int(w * 0.8), h - font_large.size - font_small.size - 32)
    icon = await hass.async_add_executor_job(_load_icon, condition, icon_size)
    if icon:
        ix = x0 + (w - icon.width) // 2
        iy = y0 + 8
        img.paste(icon, (ix, iy), icon)
        text_y = iy + icon.height + 8
    else:
        draw.text((x0 + 8, y0 + 8), condition, font=font_large, fill="black")
        text_y = y0 + h // 2

    draw.text((x0 + 8, text_y), f"{temp}{unit}", font=font_large, fill="black")
    if text_y + font_large.size + 4 + font_small.size < y1:
        draw.text((x0 + 8, text_y + font_large.size + 4), label, font=font_small, fill="gray")

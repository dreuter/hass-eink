"""Weather widget."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from homeassistant.core import HomeAssistant

_ICONS_DIR = Path(__file__).parent.parent / "icons"


def _load_icon(condition: str, size: int) -> Image.Image | None:
    path = _ICONS_DIR / f"{condition}.png"
    if not path.exists():
        return None
    return Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)


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

    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", min(h // 3, w // 5, 64))
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", min(h // 5, w // 8, 32))
    except OSError:
        font_large = ImageFont.load_default()
        font_small = font_large

    icon_size = min(int(w * 0.8), h - font_large.size - font_small.size - 32)
    icon = await hass.async_add_executor_job(_load_icon, condition, icon_size)
    if icon:
        # Paste icon centered horizontally, top portion
        ix = x0 + (w - icon.width) // 2
        iy = y0 + 8
        img.paste(icon, (ix, iy), icon)
        text_y = iy + icon.height + 8
    else:
        draw.text((x0 + 8, y0 + 8), condition, font=font_large, fill="black")
        text_y = y0 + h // 2

    draw.text((x0 + 8, text_y), f"{temp}{unit}", font=font_large, fill="black")
    draw.text((x0 + 8, text_y + font_large.size + 4), condition.replace("-", " ").title(), font=font_small, fill="gray")

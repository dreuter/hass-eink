"""Test widget — shows all 7 palette colors with labels and a color gradient."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from homeassistant.core import HomeAssistant

from ..const import BLACK, WHITE, YELLOW, RED, BLUE, GREEN

_FONTS_DIR = Path(__file__).parent.parent / "fonts"

_COLORS = [
    (BLACK,  "Black"),
    (WHITE,  "White"),
    (RED,    "Red"),
    (GREEN,  "Green"),
    (BLUE,   "Blue"),
    (YELLOW, "Yellow"),
]


async def render_test(
    hass: HomeAssistant,
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    cfg: dict,
    dither: str = "none",
) -> None:
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0

    font = ImageFont.truetype(str(_FONTS_DIR / "DejaVuSans-Bold.ttf"), max(8, h // 20))

    # Top half: color swatches with labels
    swatch_h = h // 2
    n = len(_COLORS)
    sw = w // n

    for i, (color, name) in enumerate(_COLORS):
        sx0 = x0 + i * sw
        sx1 = x0 + (i + 1) * sw
        draw.rectangle((sx0, y0, sx1 - 1, y0 + swatch_h - 1), fill=color)
        text_color = BLACK if color in (WHITE, YELLOW) else WHITE
        draw.text((sx0 + 4, y0 + swatch_h // 2 - font.size // 2), name, font=font, fill=text_color)

    # Bottom half: color wheel — render to temp image then dither
    wheel_y0 = y0 + swatch_h
    wheel_h = y1 - wheel_y0
    cy = wheel_h // 2
    cx = w // 2
    radius = min(w, wheel_h) // 2 - 4

    wheel = Image.new("RGB", (w, wheel_h), WHITE)
    wdraw = ImageDraw.Draw(wheel)

    for py in range(cy - radius, cy + radius + 1):
        for px in range(cx - radius, cx + radius + 1):
            dx, dy = px - cx, py - cy
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > radius:
                continue
            angle = math.atan2(dy, dx)
            hue = (angle + math.pi) / (2 * math.pi)  # 0..1
            sat = dist / radius                        # 0..1 (center=black, edge=full color)
            h6 = hue * 6
            hi = int(h6) % 6
            f = h6 - int(h6)
            v = int(255 * sat)
            p = 0
            q = int(v * (1 - f))
            t = int(v * f)
            rgb = [(v,t,p),(q,v,p),(p,v,t),(p,q,v),(t,p,v),(v,p,q)][hi]
            wdraw.point((px, py), fill=rgb)

    if dither != "none":
        from ..dither import dither_image
        wheel = await hass.async_add_executor_job(dither_image, wheel, dither)
    else:
        # snap to nearest palette color without dithering
        palette = np.array([c for c, _ in _COLORS], dtype=np.float32)
        arr = np.array(wheel, dtype=np.float32)
        flat = arr.reshape(-1, 3)
        dists = np.sum((flat[:, None] - palette[None]) ** 2, axis=2)
        indices = np.argmin(dists, axis=1)
        snapped = palette[indices].reshape(arr.shape).astype(np.uint8)
        wheel = Image.fromarray(snapped)

    img.paste(wheel, (x0, wheel_y0))

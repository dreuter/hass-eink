"""Dithering for the Waveshare 7-color e-ink palette.

Floyd-Steinberg uses Pillow's C quantize (~15ms for 800x480).
Atkinson and Jarvis use hitherdither (pure Python, ~20s) — only use
if quality matters more than speed.
"""
import hitherdither
from PIL import Image

from .const import DITHER_NONE, DITHER_FLOYD, BLACK, WHITE, YELLOW, RED, BLUE, GREEN

_PALETTE_COLORS = [BLACK, WHITE, YELLOW, RED, BLUE, GREEN]

_PIL_PALETTE = Image.new("P", (1, 1))
_flat = []
for _c in _PALETTE_COLORS:
    _flat.extend(_c)
_flat += [0] * (768 - len(_flat))
_PIL_PALETTE.putpalette(_flat)

_HD_PALETTE = hitherdither.palette.Palette(_PALETTE_COLORS)
_HD_ALGO_MAP = {
    "atkinson": "atkinson",
    "jarvis":   "jarvis-judice-ninke",
}


def dither_image(img: Image.Image, algorithm: str) -> Image.Image:
    if algorithm == DITHER_NONE:
        return img
    if algorithm == DITHER_FLOYD:
        return img.quantize(
            colors=len(_PALETTE_COLORS),
            palette=_PIL_PALETTE,
            dither=Image.Dither.FLOYDSTEINBERG,
        ).convert("RGB")
    algo = _HD_ALGO_MAP.get(algorithm, "atkinson")
    return hitherdither.diffusion.error_diffusion_dithering(
        img, _HD_PALETTE, algo, order=2
    ).convert("RGB")

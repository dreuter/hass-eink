"""Dithering using hitherdither with the Waveshare 7-color e-ink palette."""
import hitherdither
from PIL import Image

from .const import DITHER_NONE, BLACK, WHITE, YELLOW, RED, BLUE, GREEN

_PALETTE = hitherdither.palette.Palette([BLACK, WHITE, YELLOW, RED, BLUE, GREEN])

# Map our algorithm names to hitherdither's
_ALGO_MAP = {
    "floyd-steinberg": "floyd-steinberg",
    "atkinson":        "atkinson",
    "jarvis":          "jarvis-judice-ninke",
}


def dither_image(img: Image.Image, algorithm: str) -> Image.Image:
    if algorithm == DITHER_NONE:
        return img
    algo = _ALGO_MAP.get(algorithm, "atkinson")
    return hitherdither.diffusion.error_diffusion_dithering(
        img, _PALETTE, algo, order=2
    ).convert("RGB")

"""Dithering utilities matching the Waveshare 7-color e-ink palette."""
from __future__ import annotations

import numpy as np
from PIL import Image

from .const import DITHER_ATKINSON, DITHER_FLOYD, DITHER_JARVIS, DITHER_NONE

# Waveshare 7-color e-ink palette
# TODO: palette coverage is limited — cyan/light-blue tones map to white,
#       causing loss of detail in sky/cloud icons. Consider adding orange
#       and tuning perceptual weights for better sky reproduction.
_PALETTE = np.array([
    [0,   0,   0  ],  # Black
    [255, 255, 255],  # White
    [255, 255, 0  ],  # Yellow
    [255, 0,   0  ],  # Red
    [0,   0,   255],  # Blue
    [0,   255, 0  ],  # Green
], dtype=np.float32)

# Error diffusion kernels: (dy, dx, numerator, denominator)
_FLOYD_STEINBERG_K = [(0,1,7,16),(1,-1,3,16),(1,0,5,16),(1,1,1,16)]
_ATKINSON_K        = [(0,1,1,8),(0,2,1,8),(1,-1,1,8),(1,0,1,8),(1,1,1,8),(2,0,1,8)]
_JARVIS_K          = [
    (0,1,7,48),(0,2,5,48),
    (1,-2,3,48),(1,-1,5,48),(1,0,7,48),(1,1,5,48),(1,2,3,48),
    (2,-2,1,48),(2,-1,3,48),(2,0,5,48),(2,1,3,48),(2,2,1,48),
]

_KERNELS = {
    DITHER_FLOYD: _FLOYD_STEINBERG_K,
    DITHER_ATKINSON: _ATKINSON_K,
    DITHER_JARVIS: _JARVIS_K,
}

DIFFUSION = 0.8  # match ESP default


def _nearest(r: float, g: float, b: float) -> int:
    """Return index of nearest palette color using weighted Euclidean distance."""
    rmean = (r + _PALETTE[:, 0]) / 2
    dr = r - _PALETTE[:, 0]
    dg = g - _PALETTE[:, 1]
    db = b - _PALETTE[:, 2]
    dist = ((512 + rmean) * dr * dr) / 256 + 4 * dg * dg + ((767 - rmean) * db * db) / 256
    return int(np.argmin(dist))


def dither_image(img: Image.Image, algorithm: str) -> Image.Image:
    """Apply e-ink palette dithering. Returns a new RGB image."""
    if algorithm == DITHER_NONE or algorithm not in _KERNELS:
        return img

    kernel = _KERNELS[algorithm]
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    out = np.zeros_like(arr)

    for y in range(h):
        for x in range(w):
            r, g, b = arr[y, x]
            ci = _nearest(r, g, b)
            pr, pg, pb = _PALETTE[ci]
            out[y, x] = [pr, pg, pb]
            er = (r - pr) * DIFFUSION
            eg = (g - pg) * DIFFUSION
            eb = (b - pb) * DIFFUSION
            for dy, dx, num, den in kernel:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    arr[ny, nx, 0] += er * num / den
                    arr[ny, nx, 1] += eg * num / den
                    arr[ny, nx, 2] += eb * num / den

    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

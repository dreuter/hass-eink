"""Fast dithering for the Waveshare 7-color e-ink palette."""
import numpy as np
from PIL import Image

from .const import DITHER_NONE, DITHER_FLOYD, BLACK, WHITE, YELLOW, RED, BLUE, GREEN

_PALETTE_COLORS = np.array([BLACK, WHITE, YELLOW, RED, BLUE, GREEN], dtype=np.float32)

# Pillow palette image for fast C Floyd-Steinberg
_PIL_PALETTE = Image.new("P", (1, 1))
_flat = []
for _c in [BLACK, WHITE, YELLOW, RED, BLUE, GREEN]:
    _flat.extend(_c)
_flat += [0] * (768 - len(_flat))
_PIL_PALETTE.putpalette(_flat)

# Error diffusion kernels: list of (dx, dy, weight)
_KERNELS = {
    "atkinson": [
        (1, 0, 1/8), (2, 0, 1/8),
        (-1, 1, 1/8), (0, 1, 1/8), (1, 1, 1/8),
        (0, 2, 1/8),
    ],
    "jarvis": [
        (1, 0, 7/48), (2, 0, 5/48),
        (-2, 1, 3/48), (-1, 1, 5/48), (0, 1, 7/48), (1, 1, 5/48), (2, 1, 3/48),
        (-2, 2, 1/48), (-1, 2, 3/48), (0, 2, 5/48), (1, 2, 3/48), (2, 2, 1/48),
    ],
}


def _nearest(pixel: np.ndarray) -> np.ndarray:
    dists = np.sum((pixel - _PALETTE_COLORS) ** 2, axis=1)
    return _PALETTE_COLORS[np.argmin(dists)]


def _diffuse(img: Image.Image, kernel: list) -> Image.Image:
    from numba import njit

    palette = _PALETTE_COLORS
    kdx = np.array([dx for dx, dy, _ in kernel], dtype=np.int32)
    kdy = np.array([dy for dx, dy, _ in kernel], dtype=np.int32)
    kw  = np.array([c  for dx, dy, c  in kernel], dtype=np.float32)

    @njit(cache=True)
    def _run(buf, palette, kdx, kdy, kw):
        h, w = buf.shape[:2]
        n_colors = palette.shape[0]
        n_k = kdx.shape[0]
        for y in range(h):
            for x in range(w):
                # Clamp
                for c in range(3):
                    if buf[y, x, c] < 0: buf[y, x, c] = 0
                    if buf[y, x, c] > 255: buf[y, x, c] = 255
                # Nearest palette color
                best, best_d = 0, 1e18
                for i in range(n_colors):
                    d = 0.0
                    for c in range(3):
                        diff = buf[y, x, c] - palette[i, c]
                        d += diff * diff
                    if d < best_d:
                        best_d = d
                        best = i
                # Error
                err0 = buf[y, x, 0] - palette[best, 0]
                err1 = buf[y, x, 1] - palette[best, 1]
                err2 = buf[y, x, 2] - palette[best, 2]
                buf[y, x, 0] = palette[best, 0]
                buf[y, x, 1] = palette[best, 1]
                buf[y, x, 2] = palette[best, 2]
                # Diffuse
                for k in range(n_k):
                    nx, ny = x + kdx[k], y + kdy[k]
                    if 0 <= nx < w and 0 <= ny < h:
                        buf[ny, nx, 0] += err0 * kw[k]
                        buf[ny, nx, 1] += err1 * kw[k]
                        buf[ny, nx, 2] += err2 * kw[k]
        return buf

    buf = np.array(img, dtype=np.float32)
    buf = _run(buf, palette, kdx, kdy, kw)
    return Image.fromarray(np.clip(buf, 0, 255).astype(np.uint8))


def dither_image(img: Image.Image, algorithm: str) -> Image.Image:
    if algorithm == DITHER_NONE:
        return img
    if algorithm == DITHER_FLOYD:
        return img.quantize(
            colors=len(_PALETTE_COLORS),
            palette=_PIL_PALETTE,
            dither=Image.Dither.FLOYDSTEINBERG,
        ).convert("RGB")
    kernel = _KERNELS.get(algorithm)
    if kernel is None:
        return img
    return _diffuse(img, kernel)

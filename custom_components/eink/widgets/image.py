"""WebDAV image widget — fetches a folder listing and rotates through images."""
from __future__ import annotations

import io
import logging
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

import aiohttp
from PIL import Image, ImageDraw
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from ..coordinator import DisplayCoordinator

_LOGGER = logging.getLogger(__name__)

_WEBDAV_NS = "DAV:"
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


async def _list_webdav_images(url: str, username: str | None, password: str | None) -> list[str]:
    auth = aiohttp.BasicAuth(username, password) if username else None
    headers = {"Depth": "1"}
    async with aiohttp.ClientSession() as session:
        async with session.request("PROPFIND", url, headers=headers, auth=auth) as resp:
            resp.raise_for_status()
            body = await resp.text()

    root = ET.fromstring(body)
    base = url.rstrip("/")
    images = []
    for response in root.iter(f"{{{_WEBDAV_NS}}}response"):
        href_el = response.find(f"{{{_WEBDAV_NS}}}href")
        if href_el is None:
            continue
        href = href_el.text or ""
        if any(href.lower().endswith(ext) for ext in _IMAGE_EXTS):
            # Build absolute URL if href is a path
            if href.startswith("http"):
                images.append(href)
            else:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                images.append(f"{parsed.scheme}://{parsed.netloc}{href}")
    return sorted(images)


async def _fetch_image(url: str, username: str | None, password: str | None) -> Image.Image:
    auth = aiohttp.BasicAuth(username, password) if username else None
    async with aiohttp.ClientSession() as session:
        async with session.get(url, auth=auth) as resp:
            resp.raise_for_status()
            data = await resp.read()
    return Image.open(io.BytesIO(data)).convert("RGB")


async def render_image(
    hass: HomeAssistant,
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    cfg: dict,
    coordinator: "DisplayCoordinator",
    widget_idx: int,
) -> None:
    url = cfg.get("url")
    username = cfg.get("username")
    password = cfg.get("password")
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0

    if not url:
        draw.text((x0 + 4, y0 + 4), "No WebDAV URL configured", fill="red")
        return

    # Fetch/refresh image list if not cached
    if widget_idx not in coordinator._image_lists:
        try:
            coordinator._image_lists[widget_idx] = await _list_webdav_images(url, username, password)
            coordinator._image_indices.setdefault(widget_idx, 0)
        except Exception:
            _LOGGER.exception("Failed to list WebDAV images at %s", url)
            draw.text((x0 + 4, y0 + 4), "WebDAV error", fill="red")
            return

    image_list = coordinator._image_lists[widget_idx]
    if not image_list:
        draw.text((x0 + 4, y0 + 4), "No images found", fill="gray")
        return

    idx = coordinator._image_indices.get(widget_idx, 0) % len(image_list)
    # Advance index for next render
    coordinator._image_indices[widget_idx] = (idx + 1) % len(image_list)

    try:
        photo = await _fetch_image(image_list[idx], username, password)
    except Exception:
        _LOGGER.exception("Failed to fetch image %s", image_list[idx])
        draw.text((x0 + 4, y0 + 4), "Image fetch error", fill="red")
        return

    photo.thumbnail((w, h), Image.LANCZOS)
    # Center in bbox
    pw, ph = photo.size
    paste_x = x0 + (w - pw) // 2
    paste_y = y0 + (h - ph) // 2
    img.paste(photo, (paste_x, paste_y))

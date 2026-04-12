"""Image widget — browses a HA media source folder and rotates through images."""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from ..coordinator import DisplayCoordinator

_LOGGER = logging.getLogger(__name__)


async def _browse(hass: HomeAssistant, media_content_id: str) -> list[Path]:
    """Return local Paths for all image children of a media source folder."""
    from homeassistant.components.media_source import async_browse_media
    from homeassistant.components.media_source.local_source import LocalSource

    result = await async_browse_media(hass, media_content_id)
    source: LocalSource = hass.data["media_source"]["media_source"]

    paths = []
    for child in result.children or []:
        if child.media_class == "image" or (child.media_content_type or "").startswith("image/"):
            try:
                # media_content_id format: media-source://media_source/{source_dir_id}/{location}
                _, rest = child.media_content_id.split("media-source://media_source/", 1)
                source_dir_id, _, location = rest.partition("/")
                paths.append(source.async_full_path(source_dir_id, location))
            except Exception:
                _LOGGER.debug("Could not resolve path for %s", child.media_content_id)
    return paths


async def render_image(
    hass: HomeAssistant,
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    cfg: dict,
    coordinator: "DisplayCoordinator",
    widget_idx: int,
) -> None:
    media_content_id = cfg.get("media_content_id")
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0

    if not media_content_id:
        draw.text((x0 + 4, y0 + 4), "No media source configured", fill="gray")
        return

    if widget_idx not in coordinator._image_lists:
        try:
            coordinator._image_lists[widget_idx] = await _browse(hass, media_content_id)
            coordinator._image_indices.setdefault(widget_idx, 0)
        except Exception:
            _LOGGER.exception("Failed to browse media source %s", media_content_id)
            draw.text((x0 + 4, y0 + 4), "Media source error", fill="red")
            return

    image_list = coordinator._image_lists[widget_idx]
    if not image_list:
        draw.text((x0 + 4, y0 + 4), "No images found", fill="gray")
        return

    idx = coordinator._image_indices.get(widget_idx, 0) % len(image_list)
    coordinator._image_indices[widget_idx] = (idx + 1) % len(image_list)
    path = image_list[idx]

    try:
        photo = await hass.async_add_executor_job(lambda: Image.open(path).convert("RGB"))
    except Exception:
        _LOGGER.exception("Failed to open image %s", path)
        draw.text((x0 + 4, y0 + 4), "Image error", fill="red")
        return

    photo.thumbnail((w, h), Image.LANCZOS)
    pw, ph = photo.size
    img.paste(photo, (x0 + (w - pw) // 2, y0 + (h - ph) // 2))

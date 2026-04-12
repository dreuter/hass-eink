"""Display coordinator — holds active layout and image rotation state."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ACTIVE_LAYOUT, CONF_DITHER, CONF_LAYOUTS, CONF_TOKEN, DITHER_DEFAULT


class DisplayCoordinator:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.token: str = entry.data[CONF_TOKEN]
        self._image_indices: dict[int, int] = {}
        self._image_lists: dict[int, list[str]] = {}

    @property
    def active_layout(self) -> str:
        return self.entry.options.get(CONF_ACTIVE_LAYOUT, "default")

    @property
    def layouts(self) -> dict:
        return self.entry.options.get(CONF_LAYOUTS, {"default": []})

    @property
    def active_widgets(self) -> list[dict]:
        return self.layouts.get(self.active_layout, [])

    @property
    def dither(self) -> str:
        return self.entry.options.get(CONF_DITHER, DITHER_DEFAULT)

    async def set_layout(self, layout_name: str) -> None:
        import logging
        if layout_name not in self.layouts:
            logging.getLogger(__name__).warning(
                "Layout %s not found for display %s", layout_name, self.token
            )
            return
        self.hass.config_entries.async_update_entry(
            self.entry,
            options={**self.entry.options, CONF_ACTIVE_LAYOUT: layout_name},
        )

    async def async_get_png(self, layout_override: str | None = None) -> bytes:
        from .renderer import render_layout
        widgets = self.layouts.get(layout_override, self.active_widgets) if layout_override else self.active_widgets
        return await render_layout(self.hass, widgets, self, self.dither)

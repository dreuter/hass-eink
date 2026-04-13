"""HTTP view to expose config entry options to the panel."""
from __future__ import annotations

from http import HTTPStatus

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import CONF_DITHER, DITHER_DEFAULT, DOMAIN


class EinkOptionsView(HomeAssistantView):
    url = "/api/eink_options/{entry_id}"
    name = "api:eink:options"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        coordinator = self.hass.data.get(DOMAIN, {}).get(entry_id)
        return self.json({
            "token": entry.data.get("token", ""),
            "dither": entry.options.get(CONF_DITHER, DITHER_DEFAULT),
            "esphome_device": coordinator.esphome_device if coordinator else None,
            **entry.options,
        })

"""HTTP view — serves PNG to ESPHome devices."""
from __future__ import annotations

import logging
from http import HTTPStatus

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EinkView(HomeAssistantView):
    url = "/api/eink/{token}.png"
    name = "api:eink:png"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request, token: str) -> web.Response:
        coordinators = self.hass.data.get(DOMAIN, {})
        coordinator = next(
            (c for c in coordinators.values() if c.token == token),
            None,
        )
        if coordinator is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        # Register the ESPHome device name if provided
        device_name = request.headers.get("X-ESPHome-Device")
        if device_name:
            coordinator.esphome_device = device_name

        # Allow overriding the layout via ?layout=name for preview purposes
        layout_override = request.rel_url.query.get("layout")

        try:
            png = await coordinator.async_get_png(layout_override=layout_override)
        except Exception:
            _LOGGER.exception("Failed to render PNG for token %s", token)
            return web.Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

        return web.Response(
            body=png,
            content_type="image/png",
            headers={"Cache-Control": "no-store"},
        )

"""E-Ink Display integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import CONF_TOKEN, DOMAIN
from .coordinator import DisplayCoordinator
from .http import EinkView

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    if hass.http:
        hass.http.register_view(EinkView(hass))
    else:
        from homeassistant.components import http as http_component
        hass.bus.async_listen_once(
            "component_loaded",
            lambda event: (
                hass.http.register_view(EinkView(hass))
                if event.data.get("component") == "http"
                else None
            ),
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DisplayCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    async def handle_set_layout(call: ServiceCall) -> None:
        token = call.data.get(CONF_TOKEN)
        layout_name = call.data.get("layout")
        for coord in hass.data[DOMAIN].values():
            if isinstance(coord, DisplayCoordinator) and coord.token == token:
                await coord.set_layout(layout_name)
                break

    hass.services.async_register(
        DOMAIN,
        "set_layout",
        handle_set_layout,
        schema=None,
    )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

"""E-Ink Display integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import CONF_ACTIVE_LAYOUT, CONF_LAYOUTS, CONF_TOKEN, DOMAIN
from .coordinator import DisplayCoordinator
from .http import EinkView
from .options_view import EinkOptionsView

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    if hass.http:
        await _register_http(hass)
    else:
        async def _on_http_loaded(event):
            if event.data.get("component") == "http":
                await _register_http(hass)
        hass.bus.async_listen_once("component_loaded", _on_http_loaded)
    return True


async def _register_http(hass: HomeAssistant) -> None:
    hass.http.register_view(EinkView(hass))
    hass.http.register_view(EinkOptionsView(hass))
    from .panel import async_setup_panel
    await async_setup_panel(hass)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DisplayCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["select"])

    async def handle_set_layout(call: ServiceCall) -> None:
        token = call.data.get(CONF_TOKEN)
        layout_name = call.data.get("layout")
        for coord in hass.data[DOMAIN].values():
            if isinstance(coord, DisplayCoordinator) and coord.token == token:
                await coord.set_layout(layout_name)
                break

    async def handle_set_options(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        layouts = call.data.get(CONF_LAYOUTS)
        active_layout = call.data.get(CONF_ACTIVE_LAYOUT)
        target_entry = hass.config_entries.async_get_entry(entry_id)
        if target_entry and target_entry.domain == DOMAIN:
            hass.config_entries.async_update_entry(
                target_entry,
                options={
                    CONF_LAYOUTS: layouts,
                    CONF_ACTIVE_LAYOUT: active_layout,
                },
            )

    hass.services.async_register(DOMAIN, "set_layout", handle_set_layout)
    hass.services.async_register(DOMAIN, "set_options", handle_set_options)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_unload_platforms(entry, ["select"])
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

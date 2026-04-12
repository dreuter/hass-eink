"""Select entity for switching the active layout."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EinkLayoutSelect(coordinator, entry)])


class EinkLayoutSelect(SelectEntity):
    _attr_icon = "mdi:monitor"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_layout"
        self._attr_name = f"{entry.title} Layout"

    @property
    def options(self) -> list[str]:
        return list(self._coordinator.layouts.keys())

    @property
    def current_option(self) -> str:
        return self._coordinator.active_layout

    async def async_select_option(self, option: str) -> None:
        await self._coordinator.set_layout(option)
        self.async_write_ha_state()

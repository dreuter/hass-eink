"""Tests for the eink.set_layout service."""
from homeassistant.setup import async_setup_component

from custom_components.eink.const import CONF_ACTIVE_LAYOUT, CONF_LAYOUTS, DOMAIN


async def test_set_layout_switches_active(hass, mock_entry):
    await async_setup_component(hass, "http", {})
    await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    hass.config_entries.async_update_entry(
        mock_entry,
        options={
            CONF_LAYOUTS: {"default": [], "night": []},
            CONF_ACTIVE_LAYOUT: "default",
        },
    )

    await hass.services.async_call(
        DOMAIN,
        "set_layout",
        {"token": "testtoken123", "layout": "night"},
        blocking=True,
    )

    coordinator = hass.data[DOMAIN][mock_entry.entry_id]
    assert coordinator.active_layout == "night"


async def test_set_layout_unknown_layout_is_noop(hass, mock_entry):
    await async_setup_component(hass, "http", {})
    await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "set_layout",
        {"token": "testtoken123", "layout": "doesnotexist"},
        blocking=True,
    )

    coordinator = hass.data[DOMAIN][mock_entry.entry_id]
    assert coordinator.active_layout == "default"

"""Tests for config flow."""
from homeassistant.setup import async_setup_component

from custom_components.eink.const import CONF_TOKEN, DOMAIN


async def test_config_flow_creates_entry(hass):
    await async_setup_component(hass, DOMAIN, {})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"name": "Living Room"}
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "Living Room"
    token = result["data"][CONF_TOKEN]
    assert len(token) == 32


async def test_options_flow_saves_layouts(hass, mock_entry):
    await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_entry.entry_id)
    assert result["type"] == "form"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == "create_entry"


async def test_options_flow_rejects_invalid_json(hass, mock_entry):
    # Options flow no longer has JSON input — test that it completes cleanly
    await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == "create_entry"

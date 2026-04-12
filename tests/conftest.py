"""Shared fixtures."""
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eink.const import CONF_ACTIVE_LAYOUT, CONF_LAYOUTS, CONF_TOKEN, DOMAIN


# Required by pytest-homeassistant-custom-component to load custom integrations
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "Test Display", CONF_TOKEN: "testtoken123"},
        options={
            CONF_LAYOUTS: {"default": []},
            CONF_ACTIVE_LAYOUT: "default",
        },
    )
    entry.add_to_hass(hass)
    return entry

"""Register the e-ink panel and static assets."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PANEL_URL = f"/api/eink_panel"
WWW_PATH = Path(__file__).parent / "www"


async def async_setup_panel(hass: HomeAssistant) -> None:
    await hass.http.async_register_static_paths([
        StaticPathConfig(f"/{DOMAIN}_static", str(WWW_PATH), cache_headers=False)
    ])
    async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title="E-Ink",
        sidebar_icon="mdi:monitor",
        frontend_url_path="eink",
        config={
            "_panel_custom": {
                "name": "eink-panel",
                "js_url": f"/{DOMAIN}_static/eink-panel.js",
                "embed_iframe": False,
                "trust_external_script": True,
            }
        },
        require_admin=True,
    )

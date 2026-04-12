"""Config flow for E-Ink Display integration."""
from __future__ import annotations

import json
import os
import secrets
import base64

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_ACTIVE_LAYOUT, CONF_LAYOUTS, CONF_TOKEN, DOMAIN

DEFAULT_LAYOUT = {
    "default": []
}


class EinkConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            token = base64.urlsafe_b64encode(os.urandom(24)).decode()
            return self.async_create_entry(
                title=user_input["name"],
                data={
                    "name": user_input["name"],
                    CONF_TOKEN: token,
                },
                description_placeholders={"token": token},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("name"): str}),
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return EinkOptionsFlow()


class EinkOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=self.config_entry.options)

        token = self.config_entry.data.get(CONF_TOKEN, "")
        entry_id = self.config_entry.entry_id
        active = self.config_entry.options.get(CONF_ACTIVE_LAYOUT, "default")
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "token": token,
                "preview_url": f"/api/eink/{token}.png",
                "panel_url": f"/eink#entry={entry_id}&layout={active}",
            },
        )

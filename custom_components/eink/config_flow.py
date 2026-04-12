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
        errors = {}
        current_layouts = self.config_entry.options.get(CONF_LAYOUTS, DEFAULT_LAYOUT)
        current_active = self.config_entry.options.get(CONF_ACTIVE_LAYOUT, "default")

        if user_input is not None:
            try:
                layouts = json.loads(user_input[CONF_LAYOUTS])
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_LAYOUTS: layouts,
                        CONF_ACTIVE_LAYOUT: user_input[CONF_ACTIVE_LAYOUT],
                    },
                )
            except (json.JSONDecodeError, ValueError):
                errors[CONF_LAYOUTS] = "invalid_json"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_LAYOUTS, default=json.dumps(current_layouts, indent=2)): str,
                vol.Required(CONF_ACTIVE_LAYOUT, default=current_active): str,
            }),
            errors=errors,
            description_placeholders={
                "token": self.config_entry.data.get(CONF_TOKEN, ""),
                "preview_url": f"/api/eink/{self.config_entry.data.get(CONF_TOKEN, '')}.png",
            },
        )

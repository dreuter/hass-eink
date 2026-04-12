"""Tests for the HTTP PNG endpoint — calls the view handler directly, no live server needed."""
from unittest.mock import MagicMock

import pytest
from homeassistant.setup import async_setup_component

from custom_components.eink.const import DOMAIN
from custom_components.eink.http import EinkView


async def _call_view(hass, token: str):
    view = EinkView(hass)
    request = MagicMock()
    return await view.get(request, token)


async def test_png_endpoint_returns_image(hass, mock_entry):
    await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    resp = await _call_view(hass, "testtoken123")

    assert resp.status == 200
    assert resp.content_type == "image/png"
    assert resp.body[:4] == b"\x89PNG"


async def test_png_endpoint_unknown_token(hass, mock_entry):
    await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    resp = await _call_view(hass, "wrongtoken")
    assert resp.status == 404

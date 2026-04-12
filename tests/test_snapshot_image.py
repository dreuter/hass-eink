"""Golden master tests for the image widget."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from custom_components.eink.renderer import render_layout

FIXTURE_IMAGE = Path(__file__).parent / "fixtures" / "atlas_mountains.jpg"

SIZES = [(1, 1), (1, 4), (2, 2), (3, 4)]


def _coord_with_image():
    c = MagicMock()
    c._image_indices = {0: 0}
    c._image_lists = {0: [str(FIXTURE_IMAGE)]}
    return c


from tests.conftest import assert_no_bleed

@pytest.mark.parametrize("row_span,col_span", SIZES)
async def test_image_snapshot(hass, assert_png_snapshot, row_span, col_span):
    coord = _coord_with_image()
    with patch(
        "custom_components.eink.widgets.image._browse",
        AsyncMock(return_value=[str(FIXTURE_IMAGE)]),
    ):
        widgets = [{"type": "image", "row": 0, "col": 0,
                    "row_span": row_span, "col_span": col_span,
                    "config": {"media_content_id": "media-source://media_source/local/test"}}]
        coord._image_lists = {}
        coord._image_indices = {}
        png = await render_layout(hass, widgets, coord)
    assert_no_bleed(png, widgets)
    assert_png_snapshot(png, f"image_{row_span}x{col_span}")

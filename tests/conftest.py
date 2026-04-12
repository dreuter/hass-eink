"""Shared fixtures."""
import io
import os
from pathlib import Path

import pytest
from PIL import Image
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eink.const import CONF_ACTIVE_LAYOUT, CONF_LAYOUTS, CONF_TOKEN, DOMAIN

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


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


@pytest.fixture
def assert_png_snapshot(request):
    """Save PNG to tests/snapshots/ and compare on subsequent runs.
    Set UPDATE_SNAPSHOTS=1 to regenerate.
    """
    update = os.environ.get("UPDATE_SNAPSHOTS") == "1"

    def _assert(png: bytes, name: str) -> None:
        path = SNAPSHOT_DIR / f"{name}.png"
        if update or not path.exists():
            SNAPSHOT_DIR.mkdir(exist_ok=True)
            path.write_bytes(png)
            return
        assert png == path.read_bytes(), (
            f"Snapshot mismatch: {path} — run with UPDATE_SNAPSHOTS=1 to regenerate."
        )

    return _assert


def assert_no_bleed(png: bytes, widgets: list[dict]) -> None:
    """Assert no widget painted outside its assigned grid bbox."""
    from custom_components.eink.const import DISPLAY_WIDTH, DISPLAY_HEIGHT, GRID_COLS, GRID_ROWS
    cell_w = DISPLAY_WIDTH // GRID_COLS
    cell_h = DISPLAY_HEIGHT // GRID_ROWS

    img = Image.open(io.BytesIO(png)).convert("RGB")
    white = (255, 255, 255)

    for widget in widgets:
        r, c = widget["row"], widget["col"]
        rs, cs = widget.get("row_span", 1), widget.get("col_span", 1)
        x0, y0 = c * cell_w, r * cell_h
        x1, y1 = x0 + cs * cell_w, y0 + rs * cell_h

        # Check rows above
        for y in range(0, y0):
            for x in range(x0, x1):
                assert img.getpixel((x, y)) == white, (
                    f"Widget {widget['type']} bled above its bbox at ({x},{y})"
                )
        # Check rows below
        for y in range(y1, DISPLAY_HEIGHT):
            for x in range(x0, x1):
                assert img.getpixel((x, y)) == white, (
                    f"Widget {widget['type']} bled below its bbox at ({x},{y})"
                )
        # Check cols left
        for x in range(0, x0):
            for y in range(y0, y1):
                assert img.getpixel((x, y)) == white, (
                    f"Widget {widget['type']} bled left of its bbox at ({x},{y})"
                )
        # Check cols right
        for x in range(x1, DISPLAY_WIDTH):
            for y in range(y0, y1):
                assert img.getpixel((x, y)) == white, (
                    f"Widget {widget['type']} bled right of its bbox at ({x},{y})"
                )

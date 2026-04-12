DOMAIN = "eink"

CONF_TOKEN = "token"
CONF_LAYOUTS = "layouts"
CONF_ACTIVE_LAYOUT = "active_layout"
CONF_DITHER = "dither"
DITHER_NONE = "none"
DITHER_FLOYD = "floyd-steinberg"
DITHER_ATKINSON = "atkinson"
DITHER_JARVIS = "jarvis"
DITHER_OPTIONS = [DITHER_NONE, DITHER_FLOYD, DITHER_ATKINSON, DITHER_JARVIS]
DITHER_DEFAULT = DITHER_FLOYD

# Waveshare 7-color e-ink palette
# Color codes per Waveshare reference:
# https://github.com/waveshareteam/ESP32-S3-PhotoPainter/blob/02be1a7570e3fc586b628fb55c60a247f00ed88d/01_Example/xiaozhi-esp32/components/port_bsp/display_bsp.h#L8
# 0x0=Black, 0x1=White, 0x2=Yellow, 0x3=Red, 0x5=Blue, 0x6=Green
# (0x4 is not used — maps to white on this panel)
BLACK  = (0,   0,   0  )
WHITE  = (255, 255, 255)
YELLOW = (255, 255, 0  )
RED    = (255, 0,   0  )
BLUE   = (0,   0,   255)
GREEN  = (0,   255, 0  )

DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
GRID_ROWS = 3
GRID_COLS = 4

WIDGET_WEATHER = "weather"
WIDGET_CALENDAR = "calendar"
WIDGET_IMAGE = "image"
WIDGET_TEST = "test"

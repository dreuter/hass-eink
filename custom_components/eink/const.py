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
BLACK  = (0,   0,   0  )
WHITE  = (255, 255, 255)
YELLOW = (255, 255, 0  )
RED    = (255, 0,   0  )
BLUE   = (0,   0,   255)
GREEN  = (0,   255, 0  )
ORANGE = (255, 128, 0  )

DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
GRID_ROWS = 3
GRID_COLS = 4

WIDGET_WEATHER = "weather"
WIDGET_CALENDAR = "calendar"
WIDGET_IMAGE = "image"
WIDGET_TEST = "test"

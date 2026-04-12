# hass-eink

A Home Assistant custom integration that renders grid-based layouts (weather, calendar, WebDAV photos) to PNG and serves them to ESPHome e-ink displays.

## How it works

Each display is registered in HA and gets a unique secret token. The ESPHome device polls `GET /api/eink/{token}.png` — HA renders the current layout on demand and returns a 800×480 PNG.

```
ESPHome  ──GET /api/eink/{token}.png──▶  Home Assistant
                                              │
                                         GridRenderer
                                        ┌────┴────┐
                                    Weather  Calendar  WebDAV Image
```

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS (type: Integration).
2. Install **E-Ink Display**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/eink/` into your HA `config/custom_components/` directory and restart.

## Setup

1. Go to **Settings → Devices & Services → Add Integration** and search for **E-Ink Display**.
2. Enter a display name. A token is generated — copy it for your ESPHome config.
3. After adding, click **Configure** on the integration to define layouts.

## ESPHome configuration

```yaml
http_request:
  useragent: esphome

time:
  - platform: homeassistant
    id: ha_time

display:
  - platform: waveshare_epaper   # adjust to your display
    # ... your pins ...
    lambda: |-
      it.image(0, 0, id(eink_image));

image:
  - platform: online_image
    id: eink_image
    url: "http://homeassistant.local:8123/api/eink/YOUR_TOKEN_HERE.png"
    format: PNG
    update_interval: 5min
```

Replace `YOUR_TOKEN_HERE` with the token shown during setup.

## Layout configuration

Layouts are configured via **Settings → Devices & Services → E-Ink Display → Configure**.

The **Layouts** field accepts a JSON object where each key is a layout name and the value is a list of widget definitions:

```json
{
  "morning": [
    {
      "type": "weather",
      "row": 0, "col": 0,
      "row_span": 2, "col_span": 2,
      "config": { "entity_id": "weather.home" }
    },
    {
      "type": "calendar",
      "row": 0, "col": 2,
      "row_span": 3, "col_span": 2,
      "config": { "entity_id": "calendar.family", "max_events": 6 }
    },
    {
      "type": "image",
      "row": 2, "col": 0,
      "row_span": 1, "col_span": 2,
      "config": {
        "url": "https://nextcloud.example.com/remote.php/dav/files/user/Photos/",
        "username": "user",
        "password": "secret"
      }
    }
  ],
  "night": [
    {
      "type": "weather",
      "row": 0, "col": 0,
      "row_span": 3, "col_span": 4,
      "config": { "entity_id": "weather.home" }
    }
  ]
}
```

### Grid reference

The display is divided into a **3-row × 4-column** grid on an 800×480 canvas:

```
col:  0    1    2    3
     ┌────┬────┬────┬────┐
row 0│    │    │    │    │
     ├────┼────┼────┼────┤
row 1│    │    │    │    │
     ├────┼────┼────┼────┤
row 2│    │    │    │    │
     └────┴────┴────┴────┘
```

Each cell is 200×160 px. Widgets span multiple cells via `row_span` / `col_span`.

### Widget types

#### `weather`

| Field | Description | Default |
|---|---|---|
| `entity_id` | HA weather entity | `weather.home` |

#### `calendar`

| Field | Description | Default |
|---|---|---|
| `entity_id` | HA calendar entity | `calendar.home` |
| `max_events` | Number of events to show | `5` |

#### `image`

Fetches a WebDAV folder listing and cycles through images on each render.

| Field | Description | Required |
|---|---|---|
| `url` | WebDAV folder URL | ✅ |
| `username` | Basic auth username | |
| `password` | Basic auth password | |

## `eink.set_layout` service

Switch the active layout from an automation or script:

```yaml
service: eink.set_layout
data:
  token: "YOUR_TOKEN_HERE"
  layout: "night"
```

### Example automation — switch layout at sunrise/sunset

```yaml
automation:
  - alias: "E-Ink morning layout"
    trigger:
      - platform: sun
        event: sunrise
    action:
      - service: eink.set_layout
        data:
          token: "YOUR_TOKEN_HERE"
          layout: "morning"

  - alias: "E-Ink night layout"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: eink.set_layout
        data:
          token: "YOUR_TOKEN_HERE"
          layout: "night"
```

## Development

### Setup

Requires Python 3.13+. Uses [pyenv](https://github.com/pyenv/pyenv) to manage the version.

```bash
pyenv install 3.13
pyenv local 3.13
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-test.txt
```

### Dev scripts

Create a `.env` file in the repo root with a [long-lived access token](http://localhost:8123/profile/security):

```bash
echo "HA_TOKEN=your_token_here" > .env
```

Then use the helper scripts:

```bash
# Reload the integration (picks up Python code changes, no HA restart needed)
./scripts/reload.sh

# Restart Home Assistant (needed after manifest.json or translation changes)
./scripts/restart.sh
```

### Running locally

HA Core is installed as part of the test dependencies, so you can run it directly from the venv:

```bash
source .venv/bin/activate
mkdir -p ha-config/custom_components
ln -s $(pwd)/custom_components/eink ha-config/custom_components/eink
hass -c ha-config
```

Open `http://localhost:8123`, complete onboarding, then add **E-Ink Display** via Settings → Integrations.

### Running tests

```bash
pytest tests/ -v
```

Tests use [`pytest-homeassistant-custom-component`](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component) which spins up a real in-memory Home Assistant instance. No running HA installation is needed.

### Project structure

```
custom_components/eink/
├── __init__.py        # integration setup + eink.set_layout service
├── manifest.json      # HA metadata, Pillow requirement
├── const.py           # constants (domain, grid dimensions, widget types)
├── config_flow.py     # UI config flow (display registration) + options flow (layouts)
├── coordinator.py     # per-display state: active layout, PNG cache, image rotation index
├── http.py            # GET /api/eink/{token}.png view
├── renderer.py        # grid layout → PIL Image → PNG bytes
├── services.yaml      # eink.set_layout service schema
├── strings.json       # UI strings
├── translations/
│   └── en.json
└── widgets/
    ├── weather.py     # reads HA weather entity, draws condition + temperature
    ├── calendar.py    # calls calendar.get_events, draws upcoming event list
    └── image.py       # PROPFIND WebDAV folder, fetches and rotates images
```

## Requirements

- Home Assistant 2024.1+
- `Pillow` (installed automatically)
- Fonts: DejaVu Sans (standard on most Linux systems; falls back to PIL default if missing)

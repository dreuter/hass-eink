# ESPHome client

Ready-to-use ESPHome configuration for the Waveshare S3 PhotoPainter (7.3" e-ink display).

## Setup

1. Copy `secrets.yaml.example` to `secrets.yaml` and fill in your WiFi credentials and API key.
2. Edit `hass-eink-client.yaml` and set your `ha_url` and `eink_token` substitutions.
3. Flash with ESPHome:

```bash
esphome run hass-eink-client.yaml
```

Or add it to your ESPHome dashboard and flash from there.

## Secrets

```yaml
# secrets.yaml
wifi_ssid: "Your WiFi Name"
wifi_password: "your_wifi_password"
api_encryption_key: "generate_with: esphome generate-api-key"
```

## Refresh

The display refreshes automatically at the top of every hour. You can also trigger a manual refresh from Home Assistant using the `button.hass_eink_client_refresh_display` entity.

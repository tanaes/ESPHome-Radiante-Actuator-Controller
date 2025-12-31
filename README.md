# ESPHome Actuator Project

This workspace contains an ESPHome project for an ESP32-based actuator device. It includes ready-to-use configuration, VS Code tasks, and helper scripts.

## Prerequisites (macOS)
- Python + pipx (recommended for isolated ESPHome install)
- Optional: Docker for dashboard via container

Install pipx and ESPHome:
```zsh
brew install pipx
pipx ensurepath
pipx install esphome
```
Verify installation:
```zsh
esphome version
```

## Get Started
1. Create your secrets file:
```zsh
cp esphome/secrets.example.yaml esphome/secrets.yaml
```
Edit `esphome/secrets.yaml` with your Wi‑Fi and passwords.

2. Compile firmware:
```zsh
esphome compile esphome/actuator.yaml
```

3. First-time USB upload (replace the serial device as needed):
```zsh
esphome upload esphome/actuator.yaml --device /dev/tty.usbserial-XXXX
```

4. OTA uploads (after the first flash):
```zsh
esphome upload esphome/actuator.yaml
```

5. Dashboard (local UI at http://localhost:6052 when using container or default port when using CLI):
- CLI:
```zsh
esphome dashboard esphome
```
- Docker:
```zsh
docker compose up esphome
```

## VS Code Tasks
Use the built-in tasks for Compile, Upload (USB), Upload (OTA), and Dashboard. Open the Command Palette → "Run Task".

## Scripts
Convenience wrappers are in `scripts/`:
- `build.sh` – compile
- `upload_usb.sh [serial]` – upload via USB (default placeholder port)
- `upload_ota.sh [host]` – OTA upload (default `actuator.local`)
- `dashboard.sh` – launch dashboard in the current workspace

## Creating More Devices
Copy `esphome/actuator.yaml` to a new file, e.g. `esphome/<your_device>.yaml`, then adjust the `esphome.name`, pins, and features.

## Notes
- `esphome/secrets.yaml` is git-ignored. Keep it safe.
- This project defaults to ESP32 board `esp32dev`. Change in the YAML if needed.

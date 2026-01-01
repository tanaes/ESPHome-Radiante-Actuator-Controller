# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ESP32-S3 firmware for a 7-zone radiant floor heating controller using ESPHome. The system manages zone thermostats, temperature sensors, relay outputs, and a circulation pump with valve feedback interlocking.

## Hardware

**Development Board:** Waveshare ESP32-S3-ETH-8DI-8RO
- Documentation: https://devices.esphome.io/devices/waveshare-esp32-s3-eth-8di-8do/
- MCU: ESP32-S3-WROOM-1U-N16R8 (16MB flash, 8MB PSRAM)
- 8 digital inputs (DI1-DI8) with opto-isolation
- 8 relay outputs (DO1-DO8) via PCA9554 I2C expander
- W5500 Ethernet + WiFi connectivity
- Built-in RS485 and CANbus interfaces (repurposed for display SPI)
- PCF85063 RTC (unused)

**External Components:**
- Adafruit DS2484 I2C-to-1-Wire breakout (address 0x18) for temperature sensors
- 7x DS18B20 temperature sensors on 1-Wire bus
- WS2812 RGB status LED (GPIO38)
- 2.2" ILI9341 TFT display (320x240, SPI)

## Board Pin Mapping

| Function | GPIO | Notes |
|----------|------|-------|
| **I2C** | | |
| SDA | GPIO42 | PCA9554, DS2484, PCF85063 |
| SCL | GPIO41 | |
| **Ethernet (W5500)** | | |
| CLK | GPIO15 | |
| MOSI | GPIO13 | |
| MISO | GPIO14 | |
| CS | GPIO16 | |
| INT | GPIO12 | |
| RST | GPIO39 | |
| **Digital Inputs** | | Active-low, INPUT_PULLUP |
| DI1-DI7 | GPIO4-10 | Valve feedback (zones 1-7) |
| DI8 | GPIO11 | Reserved |
| **Relay Outputs** | | Via PCA9554 at 0x20 |
| DO1-DO7 | pins 0-6 | Zone relays |
| DO8 | pin 7 | Circulation pump |
| **TFT Display (ILI9341)** | | SD Card header + GPIO21 |
| CLK | GPIO48 | SD Card header |
| MOSI | GPIO47 | SD Card header |
| CS | GPIO45 | SD Card header |
| DC | GPIO21 | |
| RST | GPIO1 | Or tie to 3.3V |
| **Other** | | |
| RGB LED | GPIO38 | WS2812 |
| Buzzer | GPIO46 | Available, unused |

## Build and Deploy Commands

```bash
# Compile firmware
esphome compile esphome/actuator.yaml

# First-time USB upload (substitute actual serial port)
esphome upload esphome/actuator.yaml --device /dev/tty.usbserial-XXXX

# OTA upload (after initial flash)
esphome upload esphome/actuator.yaml

# Launch web dashboard (http://localhost:6052)
esphome dashboard esphome
```

Shell scripts in `scripts/` wrap these commands: `build.sh`, `upload_usb.sh`, `upload_ota.sh`, `dashboard.sh`.

VS Code tasks are configured for all operations (Cmd+Shift+P → Run Task).

## Architecture

**Main configuration:** `esphome/actuator.yaml`

Key sections:
- `globals:` - `pump_demand` boolean tracking if any zone needs heat
- `number:` - Global setpoint, pump delays, hysteresis settings
- `switch:` - 8 relay outputs via PCA9554 (zones 1-7 + pump)
- `sensor:` - 7 Dallas temperature sensors (addresses need discovery)
- `climate:` - 7 thermostat entities with heat deadband control
- `binary_sensor:` - 7 valve feedback inputs (GPIO4-10) + DI8 reserved
- `script:` - `update_pump_state` and `set_pump_demand` for pump logic
- `display:` - ILI9341 TFT showing zone status, temps, relay/valve states, network info

**Pump control logic:** Pump runs when any zone thermostat calls for heat AND that zone's valve feedback confirms open, with configurable start/stop delays to prevent cycling.

## Important Patterns

- ESPHome uses `tca9554` component for PCA9554 (register-compatible)
- All credentials use `!secret` references → stored in `esphome/secrets.yaml` (git-ignored)
- Temperature displayed in Fahrenheit (sensors return Celsius, converted via filter)
- Zone 8+ expansion ready via commented XL9535 section (address 0x21)
- Sensor addresses are placeholders - actual addresses discovered via logs after first boot
- Digital inputs use 10ms debounce filter
- IDs use snake_case: `zone1_relay`, `zone1_climate`, `zone1_temp`, etc.

## First-Time Setup

1. Copy `esphome/secrets.example.yaml` to `esphome/secrets.yaml` and fill in credentials
2. Compile and flash via USB
3. Check logs to discover actual DS18B20 sensor addresses
4. Update sensor addresses in actuator.yaml, then OTA upload

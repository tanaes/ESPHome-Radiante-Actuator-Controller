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
- W5500 Ethernet + WiFi connectivity (currently using WiFi only)
- Built-in RS485 and CANbus interfaces (unused)
- PCF85063 RTC (unused)

**External Components:**
- Adafruit DS2484 I2C-to-1-Wire breakout (address 0x18) for temperature sensors
- DS18B20 temperature sensors on 1-Wire bus (use `index: N` for auto-discovery)
- WS2812 RGB status LED (GPIO38) - uses RGB color order
- 2.2" ILI9341 TFT display (240x320 native, rotated to landscape)

## Board Pin Mapping

| Function | GPIO | Notes |
|----------|------|-------|
| **I2C** | | |
| SDA | GPIO42 | PCA9554, DS2484, PCF85063 |
| SCL | GPIO41 | |
| **Ethernet (W5500)** | | Currently disabled |
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
| CS | GPIO45 | SD Card header (strapping pin - be careful) |
| DC | GPIO21 | |
| RST | GPIO1 | |
| LED/BL | 3.3V | Backlight - connect to 3.3V |
| **Other** | | |
| RGB LED | GPIO38 | WS2812, RGB order (not GRB) |
| Buzzer | GPIO46 | Available, unused |

## Build and Deploy Commands

```bash
# Compile firmware
esphome compile esphome/actuator.yaml

# USB upload (Mac port typically /dev/cu.usbmodem21101)
esphome upload esphome/actuator.yaml --device /dev/cu.usbmodem21101

# OTA upload (after initial flash, uses mDNS)
esphome upload esphome/actuator.yaml

# View logs
esphome logs esphome/actuator.yaml --device /dev/cu.usbmodem21101

# Launch web dashboard (http://localhost:6052)
esphome dashboard esphome
```

## Architecture

**Main configuration:** `esphome/actuator.yaml`

Key sections:
- `globals:` - `pump_demand` boolean tracking if any zone needs heat
- `number:` - Global setpoint (10-30°C), pump delays, hysteresis settings
- `switch:` - 8 relay outputs via PCA9554 (zones 1-7 + pump)
- `sensor:` - Dallas temperature sensors via DS2484 1-Wire bridge
- `climate:` - 7 thermostat entities with heat deadband control
- `binary_sensor:` - 7 valve feedback inputs (GPIO4-10) + DI8 reserved
- `script:` - `update_pump_state` and `set_pump_demand` for pump logic
- `interval:` - Periodic status logging (IP, temps) and LED updates
- `display:` - ILI9341 TFT showing zone status, temps, relay/valve states, network info

**Pump control logic:** Pump runs when any zone thermostat calls for heat AND that zone's valve feedback confirms open, with configurable start/stop delays to prevent cycling.

## Important Patterns

- ESPHome uses `pca9554` component for PCA9554 I/O expander (not `tca9554`)
- All credentials use `!secret` references → stored in `esphome/secrets.yaml` (git-ignored)
- **All temperatures in Celsius** - sensors, thermostats, display all use °C
- Thermostat component always works in Celsius internally (no native °F support)
- Zone 8+ expansion ready via commented XL9535 section (address 0x21)
- Use `index: N` for temperature sensors to auto-discover addresses
- Digital inputs use 10ms debounce filter
- IDs use snake_case: `zone1_relay`, `zone1_climate`, `zone1_temp`, etc.

## Display Configuration

The ILI9341 display requires specific settings:
- `dimensions: [240, 320]` - native portrait resolution
- `rotation: 270` - rotate to landscape mode
- `invert_colors: false`
- Backlight (LED pin) connects to 3.3V

## LED Status Codes

- **Solid Green** - WiFi connected, idle
- **Orange Pulse** - Heating active (pump demand)
- **Red Fast Blink** - WiFi disconnected

## First-Time Setup

1. Copy `esphome/secrets.example.yaml` to `esphome/secrets.yaml` and fill in credentials
2. Compile and flash via USB: `esphome upload esphome/actuator.yaml --device /dev/cu.usbmodem21101`
3. Monitor logs to verify sensor discovery and WiFi connection
4. Access web interface at the IP shown in logs (also displayed on TFT)
5. Temperature sensors use `index: N` for auto-discovery - update to explicit addresses for production

## Troubleshooting

- **Display garbled**: Check SPI wiring, ensure dimensions are [240, 320] with rotation 270
- **Display black**: Verify backlight connected to 3.3V, check all SPI connections
- **Sensors showing nan**: Verify DS2484 wiring, check 1-Wire bus connections
- **Sensors showing exactly 85°C**: This is the DS18B20 power-on reset value - indicates VCC not connected or power issue. The sensor cannot complete temperature conversions without proper power. Check VCC wiring.
- **WiFi issues**: Check secrets.yaml credentials, monitor logs for connection status
- **GPIO45 warnings**: This is a strapping pin - safe to use but generates boot warnings

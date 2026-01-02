#!/usr/bin/env python3
"""
Render TFT display mockups for documentation.

This script replicates the ESPHome display lambda to generate PNG images
showing different controller states. Used for README documentation.

Usage:
    python scripts/render_display.py [output_dir]

Requirements:
    pip install Pillow
"""

import os
import sys
import math
import random
from dataclasses import dataclass
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

# Display dimensions (ILI9341 in landscape mode)
WIDTH = 320
HEIGHT = 240

# Colors (RGB tuples)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 120, 255)
ORANGE = (255, 165, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (48, 48, 48)
LIGHT_GRAY = (80, 80, 80)
DARK_RED = (80, 0, 0)

# Layout constants (from actuator.yaml)
BOX_WIDTH = 40
BOX_HEIGHT = 78
GRAPH_HEIGHT = 84
GRAPH_Y = BOX_HEIGHT
STATUS_Y = BOX_HEIGHT + GRAPH_HEIGHT + 4
GRAPH_RANGE = 6.0  # +/-6C


@dataclass
class ZoneState:
    """State of a single zone."""
    temp: Optional[float]  # None = sensor missing
    setpoint: float = 20.0
    is_heating: bool = False
    valve_open: bool = False
    error_score: int = 0
    is_disabled: bool = False
    history: list = None  # Temperature history (40 samples)

    def __post_init__(self):
        if self.history is None:
            self.history = []


@dataclass
class ControllerState:
    """Complete controller state for rendering."""
    zones: list  # List of 7 ZoneState objects
    pump_on: bool = False
    pump_demand: bool = False
    pump_history: list = None  # Boolean history (40 samples)
    global_setpoint: float = 20.0
    hysteresis: float = 0.5
    ip_address: str = "192.168.1.43"
    rssi: int = -65
    wifi_connected: bool = True
    timestamp: str = "2025-01-02 14:30:00"

    def __post_init__(self):
        if self.pump_history is None:
            self.pump_history = [False] * 40


def get_font(size: int) -> ImageFont:
    """Get a font at the specified size. Falls back to default if Roboto not available."""
    try:
        # Try to use Roboto if available
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except:
            return ImageFont.load_default()


class DisplayRenderer:
    """Renders the TFT display to a PIL Image."""

    def __init__(self):
        self.img = Image.new('RGB', (WIDTH, HEIGHT), BLACK)
        self.draw = ImageDraw.Draw(self.img)

        # Load fonts at different sizes
        self.font_xlarge = get_font(20)
        self.font_large = get_font(16)
        self.font_medium = get_font(12)
        self.font_small = get_font(10)
        self.font_tiny = get_font(8)

    def render(self, state: ControllerState) -> Image:
        """Render the complete display."""
        self.img = Image.new('RGB', (WIDTH, HEIGHT), BLACK)
        self.draw = ImageDraw.Draw(self.img)

        # Draw zone boxes
        for i, zone in enumerate(state.zones):
            self._draw_zone_box(i, zone, state.hysteresis)

        # Draw pump box
        self._draw_pump_box(state)

        # Draw status bar
        self._draw_status_bar(state)

        return self.img

    def _draw_zone_box(self, index: int, zone: ZoneState, hysteresis: float):
        """Draw a single zone box with graph."""
        x = index * BOX_WIDTH

        # Determine status
        sensor_missing = zone.temp is None
        sensor_error = not sensor_missing and 84.5 <= zone.temp <= 85.5
        safety_error = zone.error_score >= 50
        is_disabled = zone.is_disabled

        # Determine colors
        outline_color = WHITE
        text_color = WHITE
        bg_color = DARK_GRAY

        if is_disabled:
            bg_color = DARK_RED
            outline_color = RED
        elif sensor_missing:
            outline_color = GRAY
            text_color = GRAY
        elif sensor_error:
            outline_color = RED
        elif safety_error:
            bg_color = RED
        elif zone.is_heating:
            bg_color = ORANGE

        # Draw box background and outline
        self.draw.rectangle([x, 0, x + BOX_WIDTH - 2, BOX_HEIGHT - 1], fill=bg_color, outline=outline_color)

        # Zone number (top left)
        self.draw.text((x + 2, 1), f"Z{index + 1}", fill=text_color, font=self.font_tiny)

        # DIS indicator if disabled
        if is_disabled:
            self.draw.text((x + 22, 1), "DIS", fill=RED, font=self.font_tiny)

        # Temperature
        if not sensor_missing:
            self.draw.text((x + 3, 10), f"{zone.temp:.0f}", fill=text_color, font=self.font_xlarge)
        else:
            self.draw.text((x + 8, 14), "--", fill=GRAY, font=self.font_large)

        # Setpoint
        self.draw.text((x + 2, 32), f"set:{zone.setpoint:.0f}", fill=text_color, font=self.font_small)

        # HEAT indicator
        heat_y = 48
        heat_color = RED if zone.is_heating else GRAY
        if zone.is_heating:
            self.draw.ellipse([x + 3, heat_y + 1, x + 9, heat_y + 7], fill=RED)
        else:
            self.draw.ellipse([x + 3, heat_y + 1, x + 9, heat_y + 7], outline=GRAY)
        self.draw.text((x + 12, heat_y), "HEAT", fill=heat_color, font=self.font_tiny)

        # VALV indicator
        valv_y = 62
        valv_color = BLUE if zone.valve_open else GRAY
        if zone.valve_open:
            self.draw.ellipse([x + 3, valv_y + 1, x + 9, valv_y + 7], fill=BLUE)
        else:
            self.draw.ellipse([x + 3, valv_y + 1, x + 9, valv_y + 7], outline=GRAY)
        self.draw.text((x + 12, valv_y), "VALV", fill=valv_color, font=self.font_tiny)

        # Draw temperature graph
        gx, gy = x, GRAPH_Y
        gw, gh = BOX_WIDTH - 1, GRAPH_HEIGHT

        # Graph background
        graph_outline = DARK_GRAY if sensor_missing else LIGHT_GRAY
        self.draw.rectangle([gx, gy, gx + gw - 1, gy + gh - 1], fill=BLACK, outline=graph_outline)

        if not sensor_missing and zone.history:
            graph_min = zone.setpoint - GRAPH_RANGE
            graph_max = zone.setpoint + GRAPH_RANGE
            total_range = GRAPH_RANGE * 2.0

            # Setpoint line (center)
            sp_y = gy + gh // 2
            self.draw.line([gx + 1, sp_y, gx + gw - 2, sp_y], fill=GRAY)

            # Hysteresis lines (dotted)
            hyst_upper_y = gy + int((graph_max - (zone.setpoint + hysteresis)) / total_range * gh)
            hyst_lower_y = gy + int((graph_max - (zone.setpoint - hysteresis)) / total_range * gh)
            for px in range(gx + 2, gx + gw - 2, 3):
                if gy <= hyst_upper_y < gy + gh:
                    self.draw.point((px, hyst_upper_y), fill=LIGHT_GRAY)
                if gy <= hyst_lower_y < gy + gh:
                    self.draw.point((px, hyst_lower_y), fill=LIGHT_GRAY)

            # Temperature history line
            points = []
            for s, val in enumerate(zone.history[-40:]):
                if val is None or val < 0 or val > 100:
                    continue
                py = gy + int((graph_max - val) / total_range * gh)
                py = max(gy + 1, min(gy + gh - 2, py))
                px = gx + 1 + (s * (gw - 3)) // 39
                points.append((px, py))

            if len(points) > 1:
                self.draw.line(points, fill=GREEN, width=1)

    def _draw_pump_box(self, state: ControllerState):
        """Draw the pump status box."""
        pump_x = 7 * BOX_WIDTH
        bg_color = BLUE if state.pump_on else DARK_GRAY

        # Box
        self.draw.rectangle([pump_x, 0, pump_x + BOX_WIDTH - 2, BOX_HEIGHT - 1],
                           fill=bg_color, outline=WHITE)

        # PUMP label
        self.draw.text((pump_x + 4, 2), "PUMP", fill=WHITE, font=self.font_small)

        # ON/OFF status
        status_text = "ON" if state.pump_on else "OFF"
        status_color = WHITE if state.pump_on else GRAY
        self.draw.text((pump_x + 6, 18), status_text, fill=status_color, font=self.font_large)

        # DMD indicator
        pdem_y = 48
        dmd_color = ORANGE if state.pump_demand else GRAY
        if state.pump_demand:
            self.draw.ellipse([pump_x + 3, pdem_y + 1, pump_x + 9, pdem_y + 7], fill=ORANGE)
        else:
            self.draw.ellipse([pump_x + 3, pdem_y + 1, pump_x + 9, pdem_y + 7], outline=GRAY)
        self.draw.text((pump_x + 12, pdem_y), "DMD", fill=dmd_color, font=self.font_tiny)

        # RLY indicator
        prel_y = 62
        rly_color = GREEN if state.pump_on else GRAY
        if state.pump_on:
            self.draw.ellipse([pump_x + 3, prel_y + 1, pump_x + 9, prel_y + 7], fill=GREEN)
        else:
            self.draw.ellipse([pump_x + 3, prel_y + 1, pump_x + 9, prel_y + 7], outline=GRAY)
        self.draw.text((pump_x + 12, prel_y), "RLY", fill=rly_color, font=self.font_tiny)

        # Pump graph
        pgx, pgy = pump_x, GRAPH_Y
        pgw, pgh = BOX_WIDTH - 1, GRAPH_HEIGHT

        self.draw.rectangle([pgx, pgy, pgx + pgw - 1, pgy + pgh - 1], fill=BLACK, outline=LIGHT_GRAY)

        # Pump history bars
        for s, on in enumerate(state.pump_history[-40:]):
            px = pgx + 1 + (s * (pgw - 3)) // 39
            if on:
                self.draw.line([px, pgy + 2, px, pgy + pgh - 3], fill=BLUE)

    def _draw_status_bar(self, state: ControllerState):
        """Draw the bottom status bar."""
        # Line 1: Network status
        self.draw.text((5, STATUS_Y), "Net:", fill=WHITE, font=self.font_small)
        if state.wifi_connected:
            self.draw.text((30, STATUS_Y), state.ip_address, fill=GREEN, font=self.font_small)
            self.draw.text((145, STATUS_Y), f"RSSI:{state.rssi}", fill=GRAY, font=self.font_tiny)
        else:
            self.draw.text((30, STATUS_Y), "DISCONNECTED", fill=RED, font=self.font_small)

        # Line 2: Time and global setpoint
        line2_y = STATUS_Y + 14
        self.draw.text((5, line2_y), state.timestamp, fill=WHITE, font=self.font_small)
        self.draw.text((200, line2_y), f"Set:{state.global_setpoint:.1f}C", fill=WHITE, font=self.font_small)

        # Line 3: Demand and valve summary
        line3_y = line2_y + 14
        self.draw.text((5, line3_y), "Demand:", fill=WHITE, font=self.font_small)
        demand_color = ORANGE if state.pump_demand else GRAY
        demand_text = "ACTIVE" if state.pump_demand else "idle"
        self.draw.text((55, line3_y), demand_text, fill=demand_color, font=self.font_small)

        any_valve = any(z.valve_open for z in state.zones)
        self.draw.text((120, line3_y), "Valves:", fill=WHITE, font=self.font_small)
        valve_color = GREEN if any_valve else GRAY
        valve_text = "OPEN" if any_valve else "closed"
        self.draw.text((170, line3_y), valve_text, fill=valve_color, font=self.font_small)

        active_count = sum(1 for z in state.zones if z.is_heating)
        zones_color = ORANGE if active_count > 0 else GRAY
        self.draw.text((240, line3_y), f"Zones:{active_count}", fill=zones_color, font=self.font_small)


def generate_history(base_temp: float, setpoint: float, heating: bool, samples: int = 40) -> list:
    """Generate realistic temperature history."""
    history = []
    temp = base_temp - 1.0 if heating else base_temp + 0.5
    for i in range(samples):
        if heating:
            temp += random.uniform(0.02, 0.08)
        else:
            temp += random.uniform(-0.03, 0.03)
        history.append(temp)
    return history


def create_idle_state() -> ControllerState:
    """Create state showing idle/normal operation."""
    zones = []
    for i in range(7):
        if i < 2:  # Zones 1-2 have sensors
            temp = 20.5 + random.uniform(-0.5, 0.5)
            zones.append(ZoneState(
                temp=temp,
                setpoint=20.0,
                history=generate_history(temp, 20.0, False)
            ))
        else:  # Zones 3-7 no sensors
            zones.append(ZoneState(temp=None, setpoint=20.0))

    return ControllerState(zones=zones)


def create_heating_state() -> ControllerState:
    """Create state showing active heating."""
    zones = []

    # Zone 1: Heating, valve open
    zones.append(ZoneState(
        temp=19.2,
        setpoint=20.0,
        is_heating=True,
        valve_open=True,
        history=generate_history(19.2, 20.0, True)
    ))

    # Zone 2: At setpoint, idle
    zones.append(ZoneState(
        temp=20.3,
        setpoint=20.0,
        history=generate_history(20.3, 20.0, False)
    ))

    # Zones 3-7: No sensors
    for _ in range(5):
        zones.append(ZoneState(temp=None, setpoint=20.0))

    # Pump history showing recent activity
    pump_hist = [False] * 20 + [True] * 20

    return ControllerState(
        zones=zones,
        pump_on=True,
        pump_demand=True,
        pump_history=pump_hist
    )


def create_error_state() -> ControllerState:
    """Create state showing safety errors and disabled zone."""
    zones = []

    # Zone 1: Disabled due to errors
    zones.append(ZoneState(
        temp=18.5,
        setpoint=20.0,
        is_disabled=True,
        error_score=100,
        history=generate_history(18.5, 20.0, False)
    ))

    # Zone 2: Safety error (high score but not disabled)
    zones.append(ZoneState(
        temp=19.0,
        setpoint=20.0,
        is_heating=True,
        valve_open=False,  # Valve not opening - causing error
        error_score=65,
        history=generate_history(19.0, 20.0, True)
    ))

    # Zones 3-7: No sensors
    for _ in range(5):
        zones.append(ZoneState(temp=None, setpoint=20.0))

    return ControllerState(zones=zones)


def create_mixed_state() -> ControllerState:
    """Create state showing various conditions for comprehensive documentation."""
    zones = []

    # Zone 1: Heating normally
    zones.append(ZoneState(
        temp=19.5,
        setpoint=20.0,
        is_heating=True,
        valve_open=True,
        history=generate_history(19.5, 20.0, True)
    ))

    # Zone 2: At setpoint, idle
    zones.append(ZoneState(
        temp=20.8,
        setpoint=21.0,
        history=generate_history(20.8, 21.0, False)
    ))

    # Zone 3: Sensor missing
    zones.append(ZoneState(temp=None, setpoint=20.0))

    # Zone 4: Sensor error (85C)
    zones.append(ZoneState(
        temp=85.0,
        setpoint=20.0,
        history=[85.0] * 40
    ))

    # Zone 5: Safety warning
    zones.append(ZoneState(
        temp=18.0,
        setpoint=20.0,
        is_heating=True,
        valve_open=True,
        error_score=55,
        history=generate_history(18.0, 20.0, True)
    ))

    # Zone 6: Disabled
    zones.append(ZoneState(
        temp=17.5,
        setpoint=20.0,
        is_disabled=True,
        error_score=100,
        history=generate_history(17.5, 20.0, False)
    ))

    # Zone 7: No sensor
    zones.append(ZoneState(temp=None, setpoint=20.0))

    pump_hist = [False] * 10 + [True] * 30

    return ControllerState(
        zones=zones,
        pump_on=True,
        pump_demand=True,
        pump_history=pump_hist
    )


def main():
    """Generate all display mockups."""
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "docs/images"
    os.makedirs(output_dir, exist_ok=True)

    renderer = DisplayRenderer()

    # Generate different states
    states = {
        "display_idle": create_idle_state(),
        "display_heating": create_heating_state(),
        "display_error": create_error_state(),
        "display_mixed": create_mixed_state(),
    }

    for name, state in states.items():
        img = renderer.render(state)

        # Scale up 2x for better visibility in docs
        img_scaled = img.resize((WIDTH * 2, HEIGHT * 2), Image.Resampling.NEAREST)

        path = os.path.join(output_dir, f"{name}.png")
        img_scaled.save(path)
        print(f"Generated: {path}")

    print(f"\nAll images saved to {output_dir}/")


if __name__ == "__main__":
    main()

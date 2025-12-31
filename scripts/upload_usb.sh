#!/usr/bin/env zsh
set -euo pipefail
port="${1:-/dev/tty.usbserial-XXXX}"
esphome upload esphome/actuator.yaml --device "$port"

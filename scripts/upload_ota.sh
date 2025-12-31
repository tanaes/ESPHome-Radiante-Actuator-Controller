#!/usr/bin/env zsh
set -euo pipefail
host="${1:-actuator.local}"
esphome upload esphome/actuator.yaml --device "$host"

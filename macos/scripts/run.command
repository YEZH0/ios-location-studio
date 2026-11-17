#!/bin/zsh
set -eu
cd "${0:A:h}/.."
python3 -m uv sync --locked
exec python3 -m uv run --no-sync ios-location-studio-mac

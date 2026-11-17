#!/bin/zsh
set -eu
cd "${0:A:h}/.."
if ! python3 -c 'import sys; assert sys.version_info >= (3,11)' 2>/dev/null; then
  print '需要 Python 3.11+，请从 https://www.python.org/downloads/macos/ 安装。'; exit 1
fi
if ! python3 -m uv --version >/dev/null 2>&1; then
  python3 -m pip install --user uv
fi
python3 -m uv sync --locked
print '安装完成。双击 run.command 启动。'

"""Command line entry point: serve the control panel and open a browser."""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from . import __version__
from .brand import BRAND, DISCLAIMER_SHORT, TUTORIAL_HINT

DEFAULT_PORT = 8899


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.4)
        return probe.connect_ex((host if host != "0.0.0.0" else "127.0.0.1", port)) != 0


def _pick_port(host: str, preferred: int) -> int:
    for candidate in range(preferred, preferred + 20):
        if _port_is_free(host, candidate):
            return candidate
    raise SystemExit(f"端口 {preferred}-{preferred + 19} 全部被占用，请用 --port 指定其他端口。")


def _open_browser_later(url: str, delay: float = 1.2) -> None:
    def worker() -> None:
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001 - headless environments
            pass

    threading.Thread(target=worker, daemon=True).start()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ios-location-studio",
        description="在浏览器里为 iPhone 模拟定位（走 Apple DVT 调试通道，无需越狱、无需 MFi 证书）。",
    )
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1，仅本机可访问）")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"监听端口（默认 {DEFAULT_PORT}，被占用时自动 +1）")
    parser.add_argument("--no-browser", action="store_true", help="启动后不自动打开浏览器")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    port = _pick_port(args.host, args.port)
    display_host = "127.0.0.1" if args.host in ("0.0.0.0", "::") else args.host
    url = f"http://{display_host}:{port}/"

    banner = f"""
  iOS Location Studio {__version__}  ·  {BRAND}
  ---------------------------------------------
  控制台   {url}
  接口文档 {url}docs
  提示     保持 iPhone 解锁并通过 USB 连接；
           会话结束或断开连接时，真实定位会自动恢复。
  教程     {TUTORIAL_HINT}
  停止     Ctrl+C
  ---------------------------------------------
  {DISCLAIMER_SHORT}
  仅限 iOS 技术研究，禁止考勤打卡 / 游戏作弊 / 活动薅羊毛 / 轨迹造假。
  完整免责声明见 {url} 侧栏，或 /api/brand 的 disclaimer 字段。
"""
    print(banner, flush=True)

    if not args.no_browser:
        _open_browser_later(url)

    try:
        uvicorn.run(
            "ios_location_studio.server:app",
            host=args.host,
            port=port,
            log_level="warning",
            access_log=False,
        )
    except KeyboardInterrupt:
        print("\n已停止，真实定位已恢复。", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

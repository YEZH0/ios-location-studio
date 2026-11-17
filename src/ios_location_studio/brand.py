"""Single source of truth for branding and attribution.

Everything user-visible about the author lives here so that it is served from
one place: the web panel, the JSON API and the terminal banner all read from
this module. That makes the attribution hard to strip by editing a single
template - the strings are re-injected at runtime from the backend.
"""

from __future__ import annotations

import hashlib
from typing import Any

# --- identity -------------------------------------------------------------

BRAND = "欧耶哥爱数码"
# ASCII handle for places that cannot carry UTF-8 (HTTP headers, slugs, tags).
BRAND_SLUG = "ouyege-aishuma"
AUTHOR = "YEZH0"
AUTHOR_NAME = "YEZHI"
HOMEPAGE = "https://github.com/YEZH0/ios-location-studio"

# Channels where the full walkthrough lives. Keep the keyword identical across
# platforms so a single search finds the tutorial.
TUTORIAL_KEYWORD = "欧耶哥爱数码"

# Promo image shipped inside the package so a fresh `pip install` carries it
# too. The author's own artwork: both QR codes on one banner, used as-is.
ASSET_BASE = "/static/assets"
PROMO_IMAGE = f"{ASSET_BASE}/follow-banner.jpg"

CHANNELS: list[dict[str, str]] = [
    {"platform": "抖音", "handle": TUTORIAL_KEYWORD, "icon": "dy"},
    {"platform": "小红书", "handle": TUTORIAL_KEYWORD, "icon": "xhs"},
]

TUTORIAL_HINT = f"抖音 / 小红书 搜「{TUTORIAL_KEYWORD}」领取详细使用教程"
TUTORIAL_LONG = (
    f"完整教程、开发者模式开启步骤、认证失败排查、多设备切换，"
    f"请到抖音或小红书搜索「{TUTORIAL_KEYWORD}」。"
)

# Shown in the panel footer; short enough for one line on a 386px sidebar.
FOOTER_NOTE = f"{BRAND} · 原创工具，转载请注明出处"

# --- disclaimer ------------------------------------------------------------

# Kept as separate paragraphs (not one blob) so the panel can render a list,
# the README can render a blockquote and the API returns a structured array.
# The wording is deliberately blunt: it is the only thing standing between a
# research tool and being used for attendance fraud.
DISCLAIMER_TITLE = "免责声明"
DISCLAIMER_SHORT = "仅供 iOS 技术研究 · 禁止考勤打卡、游戏作弊、薅羊毛等欺诈用途"

DISCLAIMER: list[str] = [
    "本项目基于苹果 Xcode 调试私有 DTSimulateLocation 协议实现，仅面向 iOS 开发者做定位相关功能技术研究。",
    "本项目仅用于验证 Apple Watch 健康功能地区限制（高血压通知）的技术实验，"
    "禁止用于企业考勤打卡、游戏作弊、活动薅羊毛、轨迹造假、虚假报备等欺诈、规避风控场景。",
    "通过本工具跨地区解锁 Watch 医疗类功能，违反 Apple 用户协议；"
    "该健康通知未经过国内药监审批，结果不能作为医疗诊断参考。",
    "使用者自行承担 Apple 账号风控、设备功能失效、平台封禁等全部后果，"
    "项目作者不对违规使用承担任何责任。衍生分发遵循原开源协议。",
]

# Stamped into the consent record kept by the browser. If the wording above
# ever changes, the stamp changes with it and every user is asked again - a
# silent edit to the disclaimer must not inherit old consent.
CONSENT_VERSION = hashlib.sha1("||".join(DISCLAIMER).encode("utf-8")).hexdigest()[:8]


def brand_payload() -> dict[str, Any]:
    """Serialisable branding block attached to every status response."""
    return {
        "brand": BRAND,
        "author": AUTHOR,
        "author_name": AUTHOR_NAME,
        "homepage": HOMEPAGE,
        "tutorial_keyword": TUTORIAL_KEYWORD,
        "tutorial_hint": TUTORIAL_HINT,
        "tutorial_long": TUTORIAL_LONG,
        "footer_note": FOOTER_NOTE,
        "channels": CHANNELS,
        "promo_image": PROMO_IMAGE,
        "disclaimer_title": DISCLAIMER_TITLE,
        "disclaimer_short": DISCLAIMER_SHORT,
        "disclaimer": DISCLAIMER,
        "consent_version": CONSENT_VERSION,
    }

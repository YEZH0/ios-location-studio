"""Single source of truth for branding and attribution.

Everything user-visible about the author lives here so that it is served from
one place: the web panel, the JSON API and the terminal banner all read from
this module. That makes the attribution hard to strip by editing a single
template - the strings are re-injected at runtime from the backend.
"""

from __future__ import annotations

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
    }

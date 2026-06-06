"""B站 API 客户端：视频信息、播放器信息（含字幕列表）、字幕内容下载。"""

from typing import Any

import requests

from . import signing

# ── 常量 ────────────────────────────────────────────────────────────────────

_REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}

_VIDEO_INFO_URL = "https://api.bilibili.com/x/web-interface/wbi/view"
_PLAYER_INFO_URL = "https://api.bilibili.com/x/player/wbi/v2"


# ── 内部辅助 ────────────────────────────────────────────────────────────────

def _build_headers(cookie: str | None = None) -> dict[str, str]:
    """构建请求头，可选附加 SESSDATA cookie 用于登录态请求。"""
    headers = dict(_REQUEST_HEADERS)
    if cookie:
        headers["Cookie"] = f"SESSDATA={cookie}"
    return headers


# ── 公开 API ────────────────────────────────────────────────────────────────

def fetch_video_info(
    bvid: str, mixin_key: str, cookie: str | None = None
) -> dict[str, Any]:
    """获取视频基本信息：标题、AID、分P 列表。

    Args:
        bvid: 视频 BVID，如 BV1xx4x1x7xx。
        mixin_key: 从 signing.fetch_mixin_key() 获取的 WBI 签名密钥。
        cookie: 可选的 SESSDATA 值，用于登录态请求。

    Returns:
        包含 title, aid, pages 等字段的字典。

    Raises:
        RuntimeError: API 返回非零 code。
        requests.RequestException: 网络请求失败。
    """
    params = signing.add_wbi_signature({"bvid": bvid}, mixin_key)
    resp = requests.get(
        _VIDEO_INFO_URL,
        params=params,
        headers=_build_headers(cookie),
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 0:
        raise RuntimeError(f"获取视频信息失败: {body.get('message', '未知错误')}")
    return body["data"]


def fetch_player_info(
    aid: int, cid: int, mixin_key: str, cookie: str | None = None
) -> dict[str, Any]:
    """获取播放器信息，包含字幕列表。

    Args:
        aid: 视频 AID。
        cid: 分P 的 CID。
        mixin_key: WBI 签名密钥。
        cookie: 可选的 SESSDATA 值。无 cookie 时大部分视频的字幕列表为空。

    Returns:
        包含 subtitle.subtitles 等字段的字典。

    Raises:
        RuntimeError: API 返回非零 code。
        requests.RequestException: 网络请求失败。
    """
    params = signing.add_wbi_signature({"aid": aid, "cid": cid}, mixin_key)
    resp = requests.get(
        _PLAYER_INFO_URL,
        params=params,
        headers=_build_headers(cookie),
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 0:
        raise RuntimeError(f"获取播放器信息失败: {body.get('message', '未知错误')}")
    return body["data"]


def fetch_subtitle_items(subtitle_url: str) -> list[dict[str, Any]]:
    """从 CDN 下载字幕 JSON 并返回条目列表。

    B站字幕 JSON 结构为 {"body": [{"from": ..., "to": ..., "content": ...}, ...]}，
    此函数提取 body 字段。

    Args:
        subtitle_url: 播放器信息中返回的字幕 CDN URL。

    Returns:
        字幕条目列表，每项包含 from, to, content 字段。
    """
    if subtitle_url.startswith("//"):
        subtitle_url = "https:" + subtitle_url
    resp = requests.get(subtitle_url, headers=_REQUEST_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("body", [])

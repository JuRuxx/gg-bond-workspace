"""B站 WBI 签名：获取 mixin key 并为请求参数添加签名。"""

import hashlib
import time
import urllib.parse
from typing import Any

import requests

# ── 常量 ────────────────────────────────────────────────────────────────────

_STATIC_MIXIN_KEY = "7cd084941338484aae1ad9425b84077a"
_NAV_URL = "https://api.bilibili.com/x/web-interface/nav"

_REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}


def fetch_mixin_key() -> str:
    """从 B站 nav 接口获取 WBI mixin key，失败时返回静态后备。

    返回的 mixin key 是从 img_url 和 sub_url 文件名中提取的 32 字符拼接值。
    网络请求失败或数据缺失时，回退到内置静态 key。
    """
    try:
        resp = requests.get(_NAV_URL, headers=_REQUEST_HEADERS, timeout=5)
        data = resp.json().get("data", {})
        wbi_img = data.get("wbi_img", {})
        img_url: str = wbi_img.get("img_url", "")
        sub_url: str = wbi_img.get("sub_url", "")
        if img_url and sub_url:
            img_key = img_url.rsplit("/", 1)[-1].split(".")[0][:16]
            sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0][:16]
            return img_key + sub_key
    except Exception:
        pass
    return _STATIC_MIXIN_KEY


def add_wbi_signature(
    params: dict[str, Any], mixin_key: str
) -> dict[str, Any]:
    """为参数字典添加 wts（时间戳）和 w_rid（MD5 签名）。

    返回新字典，不修改原始 params。
    签名字符串 = 按 key 排序的 URL 编码查询串 + mixin_key，结果取 MD5 十六进制。
    """
    signed = dict(params)
    signed["wts"] = int(time.time())
    query_string = urllib.parse.urlencode(sorted(signed.items()))
    signature = hashlib.md5((query_string + mixin_key).encode()).hexdigest()
    signed["w_rid"] = signature
    return signed

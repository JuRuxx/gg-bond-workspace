"""B站 BVID 与 AID 互转，以及从 URL 中提取 BVID。

编解码使用 ENCODE_MAP 进行位置映射，确保 bvid_to_aid ↔ aid_to_bvid 互逆。
"""

import re

# ── BVID 编码常量 ──────────────────────────────────────────────────────────

_XOR_CODE = 23442827791579
_MASK_CODE = 2251799813685247
_MAX_AID = 1 << 51
_BASE58_ALPHABET = "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf"
_BASE58_MAP: dict[str, int] = {c: i for i, c in enumerate(_BASE58_ALPHABET)}
_BVID_LENGTH = 12

# ENCODE_MAP[i] = 第 i 个 base58 数字在 BVID 字符串中的位置
# 编码时：从低位到高位，按 ENCODE_MAP 放置字符
# 解码时：按 ENCODE_MAP 从高位到低位还原数值
_ENCODE_MAP = [6, 2, 7, 10, 1, 9, 8, 3, 4, 0, 5, 11]

# URL → BVID 提取正则模式列表
_BVID_PATTERNS: list[re.Pattern] = [
    re.compile(r"/video/(BV[a-zA-Z0-9]+)"),
    re.compile(r"bvid=(BV[a-zA-Z0-9]+)"),
    re.compile(r"/BV([a-zA-Z0-9]+)"),
    re.compile(r"^(BV[a-zA-Z0-9]+)$"),
]


def bvid_to_aid(bvid: str) -> int:
    """将 BVID 字符串（12 位）转换为 AID 整数。

    解码过程：按 ENCODE_MAP 从高位到低位读取 12 位字符，
    对 base58 数值取 mask 后异或得到 AID。
    与 aid_to_bvid 互为逆运算。
    """
    bvid = bvid.strip()
    if len(bvid) != _BVID_LENGTH:
        raise ValueError(f"BVID 长度应为 {_BVID_LENGTH}，实际: {len(bvid)}")

    numeric = 0
    for exp in range(_BVID_LENGTH - 1, -1, -1):
        pos = _ENCODE_MAP[exp]
        digit = _BASE58_MAP[bvid[pos]]
        numeric = numeric * 58 + digit
    return (numeric & _MASK_CODE) ^ _XOR_CODE


def aid_to_bvid(aid: int) -> str:
    """将 AID 整数转换为 BVID 字符串（12 位，含 BV 前缀）。

    编码过程：AID 异或后置最高位，取 12 次 base58 除法余数，
    按 ENCODE_MAP 放置到 BVID 的对应位置。
    """
    tmp = (aid ^ _XOR_CODE) | _MAX_AID
    chars: list[str] = [""] * _BVID_LENGTH
    for i in range(_BVID_LENGTH):
        chars[_ENCODE_MAP[i]] = _BASE58_ALPHABET[tmp % 58]
        tmp //= 58
    return "".join(chars)


def extract_bvid(url: str) -> str:
    """从 B站视频 URL 的各种常见格式中提取 BVID。

    支持的 URL 格式：
        - https://www.bilibili.com/video/BV1xx4x1x7xx
        - https://www.bilibili.com/video/BV1xx4x1x7xx?p=1
        - https://b23.tv/BV1xx4x1x7xx
        - 纯 BVID 字符串：BV1xx4x1x7xx

    Raises:
        ValueError: 无法从输入中提取合法的 BVID。
    """
    for pattern in _BVID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    raise ValueError(f"无法从 URL 中提取 BVID: {url}")

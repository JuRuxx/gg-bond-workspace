"""字幕格式转换：SRT 字幕、纯文本、JSON 序列化以及文件名清理。"""

import json
import re
from typing import Any


def seconds_to_srt_timestamp(seconds: float) -> str:
    """将秒数转换为 SRT 时间码格式 ``HH:MM:SS,mmm``。"""
    total_seconds = round(seconds, 3)
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    secs = int(total_seconds % 60)
    millis = round((total_seconds - int(total_seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def convert_to_srt(items: list[dict[str, Any]]) -> str:
    """将字幕条目列表转换为 SRT 格式字符串。

    每个条目应包含 ``from``（起始秒数）、``to``（结束秒数）、``content``（文本）。
    """
    blocks: list[str] = []
    for index, item in enumerate(items, start=1):
        start = seconds_to_srt_timestamp(item.get("from", 0))
        end = seconds_to_srt_timestamp(item.get("to", 0))
        content = item.get("content", "")
        blocks.append(f"{index}\n{start} --> {end}\n{content}\n")
    return "\n".join(blocks)


def convert_to_txt(items: list[dict[str, Any]]) -> str:
    """将字幕条目列表转换为带时间戳的纯文本，每行格式 ``[HH:MM:SS,mmm] 内容``。"""
    lines: list[str] = []
    for item in items:
        timestamp = seconds_to_srt_timestamp(item.get("from", 0))
        content = item.get("content", "")
        lines.append(f"[{timestamp}] {content}")
    return "\n".join(lines)


def convert_to_json_string(items: list[dict[str, Any]]) -> str:
    """将字幕条目列表序列化为缩进格式的 JSON 字符串（UTF-8，不转义 Unicode）。"""
    return json.dumps(items, ensure_ascii=False, indent=2)


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法和不规范字符。

    移除中文/日文引号和括号，替换操作系统非法字符为下划线。
    """
    # 移除中文/日文引号和特殊括号
    cleaned = re.sub(r'["""''〈〉《》「」『』【】（）]', "", name)
    # 替换文件系统非法字符
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", cleaned)
    return cleaned.strip()

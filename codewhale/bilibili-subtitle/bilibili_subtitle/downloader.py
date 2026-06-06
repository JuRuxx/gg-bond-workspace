"""字幕下载流程编排。

将 API 获取、格式转换、文件写入串联为完整的下载流水线。
"""

import os
from typing import Any

from . import api, export
from .signing import fetch_mixin_key

# ── 类型别名 ────────────────────────────────────────────────────────────────

_SubtitleList = list[dict[str, Any]]
_PageList = list[dict[str, Any]]


# ── 公开 API ────────────────────────────────────────────────────────────────

def download_video_subtitles(
    bvid: str,
    cookie: str | None = None,
    output_dir: str = "./subtitles",
    fmt: str = "srt",
    page_index: int | None = None,
    language_filter: set[str] | None = None,
) -> _PageList:
    """下载指定 BVID 视频的所有字幕。

    Args:
        bvid: 视频 BVID。
        cookie: SESSDATA 值，许多视频需要登录态才能获取字幕列表。
        output_dir: 字幕文件输出目录。
        fmt: 输出格式：srt / txt / json / all。
        page_index: 指定分P（1-based），None 表示全部。
        language_filter: 语言代码集合（如 {"zh", "en"}），None 表示全部。

    Returns:
        每页的下载结果列表，每项包含 page, title, subtitles 字段。
    """
    mixin_key = fetch_mixin_key()

    print(f"🔍 获取视频信息: {bvid}")
    video_info = api.fetch_video_info(bvid, mixin_key, cookie=cookie)

    title = video_info["title"]
    aid = video_info["aid"]
    pages = video_info.get("pages", [])

    if not pages:
        print("❌ 未找到视频分P")
        return []

    pages_to_process = _resolve_pages(pages, page_index)
    if len(pages_to_process) > 1:
        print(f"📦 该视频有 {len(pages_to_process)} 个分P")

    os.makedirs(output_dir, exist_ok=True)

    results: _PageList = []
    for page_number, page in pages_to_process:
        result = _process_one_page(
            page_number=page_number,
            page=page,
            total_pages=len(pages),
            aid=aid,
            title=title,
            mixin_key=mixin_key,
            cookie=cookie,
            output_dir=output_dir,
            fmt=fmt,
            language_filter=language_filter,
        )
        results.append(result)

    return results


def print_download_summary(
    results: _PageList, output_dir: str
) -> None:
    """打印下载汇总信息。"""
    total_files = sum(len(r.get("subtitles", [])) for r in results)
    print(f"\n{'=' * 50}")
    print(f"✅ 完成! 共下载 {total_files} 个字幕文件")
    print(f"📁 保存在: {os.path.abspath(output_dir)}")


# ── 内部分P解析 ────────────────────────────────────────────────────────────

def _resolve_pages(
    pages: list[dict[str, Any]], page_index: int | None
) -> list[tuple[int, dict[str, Any]]]:
    """从分P列表中筛选目标分P。

    Args:
        pages: 视频的全部分P列表。
        page_index: 目标分P编号（1-based），None 表示全部。

    Returns:
        (页码, 分P数据) 元组列表。
    """
    if page_index is not None:
        if 1 <= page_index <= len(pages):
            return [(page_index, pages[page_index - 1])]
        raise ValueError(
            f"分P {page_index} 不存在，该视频有 {len(pages)} 个分P"
        )
    return [(idx, page) for idx, page in enumerate(pages, start=1)]


# ── 单页处理 ────────────────────────────────────────────────────────────────

def _process_one_page(
    page_number: int,
    page: dict[str, Any],
    total_pages: int,
    aid: int,
    title: str,
    mixin_key: str,
    cookie: str | None,
    output_dir: str,
    fmt: str,
    language_filter: set[str] | None,
) -> dict[str, Any]:
    """下载单个分P的字幕。"""
    cid = page["cid"]
    part_title = page.get("part", f"P{page_number}")
    print(f"\n📄 [{page_number}/{total_pages}] {part_title} (cid={cid})")

    player_info = api.fetch_player_info(aid, cid, mixin_key, cookie=cookie)
    subtitle_list = player_info.get("subtitle", {}).get("subtitles", [])

    if not subtitle_list:
        _warn_no_subtitle(cookie)
        return {"page": page_number, "title": part_title, "subtitles": []}

    page_results = _fetch_and_save_subtitles(
        subtitle_list=subtitle_list,
        title=title,
        part_title=part_title,
        output_dir=output_dir,
        fmt=fmt,
        language_filter=language_filter,
    )

    return {"page": page_number, "title": part_title, "subtitles": page_results}


def _fetch_and_save_subtitles(
    subtitle_list: _SubtitleList,
    title: str,
    part_title: str,
    output_dir: str,
    fmt: str,
    language_filter: set[str] | None,
) -> _SubtitleList:
    """遍历字幕列表，下载并保存符合条件的字幕。"""
    results: _SubtitleList = []
    for sub in subtitle_list:
        lang_code = sub.get("lan", "unknown")
        lang_label = sub.get("lan_doc", lang_code)
        subtitle_url = sub.get("subtitle_url", "")

        if language_filter is not None and not _language_matches(
            lang_code, language_filter
        ):
            print(f"   ⏭️  跳过: {lang_label} ({lang_code})")
            continue

        if not subtitle_url:
            print(f"   ⚠️  {lang_label}: 无字幕 URL")
            continue

        print(f"   📥 下载字幕: {lang_label} ({lang_code})")

        try:
            items = api.fetch_subtitle_items(subtitle_url)
        except Exception as exc:
            print(f"   ❌ 下载失败: {exc}")
            continue

        if not items:
            print(f"   ⚠️  字幕为空")
            continue

        saved = _write_subtitle_files(
            items=items,
            title=title,
            part_title=part_title,
            lang_label=lang_label,
            lang_code=lang_code,
            output_dir=output_dir,
            fmt=fmt,
        )
        results.extend(saved)

    return results


# ── 语言匹配 ────────────────────────────────────────────────────────────────

def _language_matches(lang_code: str, language_filter: set[str]) -> bool:
    """检查语言代码是否匹配过滤条件。

    匹配规则：精确匹配，或过滤项出现在连字符分隔的子标签中。
    例如 "zh" 同时匹配 "zh"、"zh-CN" 和 "ai-zh"。
    """
    return any(
        lang_code == code or code in lang_code.split("-")
        for code in language_filter
    )


# ── 文件写入 ────────────────────────────────────────────────────────────────

def _write_subtitle_files(
    items: _SubtitleList,
    title: str,
    part_title: str,
    lang_label: str,
    lang_code: str,
    output_dir: str,
    fmt: str,
) -> _SubtitleList:
    """将字幕条目写入文件，支持多格式导出。"""
    safe_title = export.sanitize_filename(title)[:60]
    safe_part = export.sanitize_filename(part_title)[:30]
    base_name = f"{safe_title} - {safe_part} - {lang_label}"

    extensions = [fmt] if fmt != "all" else ["srt", "txt", "json"]
    results: _SubtitleList = []

    for ext in extensions:
        filename = f"{base_name}.{ext}"
        filepath = os.path.join(output_dir, filename)

        content = _format_items(items, ext)
        if content is None:
            continue

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"   ✅ 保存: {filename}")
        results.append(
            {"filepath": filepath, "lang": lang_code, "format": ext}
        )

    return results


_FORMATTERS: dict[str, Any] = {
    "srt": export.convert_to_srt,
    "txt": export.convert_to_txt,
    "json": export.convert_to_json_string,
}


def _format_items(
    items: _SubtitleList, extension: str
) -> str | None:
    """根据扩展名选择合适的格式化函数并返回结果。"""
    formatter = _FORMATTERS.get(extension)
    return formatter(items) if formatter else None


# ── 警告输出 ────────────────────────────────────────────────────────────────

def _warn_no_subtitle(cookie: str | None) -> None:
    """打印无可用字幕的警告信息。"""
    if cookie:
        print("   ⚠️  该分P没有可用字幕")
    else:
        print(
            "   ⚠️  该分P没有可用字幕"
            "（许多视频需要登录态才能获取字幕，请用 -c 提供 SESSDATA cookie）"
        )

"""B站字幕下载工具 — 命令行入口。"""

import argparse
import os
import sys

from . import downloader
from .bvid import extract_bvid


def parse_arguments(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="B站视频字幕下载工具（支持多 URL 批量下载）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
单 URL:
  python3 bili_sub.py "https://www.bilibili.com/video/BV..." -C sessdata.txt

多 URL（命令行）:
  python3 bili_sub.py "https://..." "https://..." -C sessdata.txt

多 URL（文件，每行一个）:
  python3 bili_sub.py -U urls.txt -C sessdata.txt

Cookie 获取:
  浏览器登录 bilibili.com → F12 → Application → Cookies → SESSDATA""",
    )
    parser.add_argument(
        "url",
        nargs="*",
        default=None,
        help="B站视频 URL 或 BVID（可多个，与 --url-file 二选一）",
    )
    parser.add_argument(
        "-U",
        "--url-file",
        default=None,
        metavar="FILE",
        help="从文件读取视频 URL（每行一个）",
    )
    parser.add_argument(
        "-c", "--cookie", default=None, help="SESSDATA cookie 值"
    )
    parser.add_argument(
        "-C",
        "--cookie-file",
        default=None,
        metavar="FILE",
        help="从文件读取 SESSDATA cookie（文件内容第一行）",
    )
    parser.add_argument(
        "-f",
        "--format",
        default="srt",
        choices=["srt", "txt", "json", "all"],
        help="输出格式 (默认: srt)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="./subtitles",
        help="输出目录 (默认: ./subtitles)",
    )
    parser.add_argument(
        "-p",
        "--page",
        type=int,
        default=None,
        help="下载指定分P (从1开始, 默认: 全部)",
    )
    parser.add_argument(
        "-l",
        "--lang",
        default="zh",
        help="语言过滤: zh/en/ja/... 多个用逗号分隔, 'all' 下载全部 (默认: zh)",
    )
    return parser.parse_args(argv)


def _read_first_line(filepath: str, label: str) -> str:
    """读取文件的第一行非空内容。"""
    if not os.path.isfile(filepath):
        print(f"❌ {label} 文件不存在: {filepath}")
        sys.exit(1)
    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    return stripped
    except OSError as exc:
        print(f"❌ 无法读取 {label} 文件: {exc}")
        sys.exit(1)
    print(f"❌ {label} 文件为空: {filepath}")
    sys.exit(1)


def _read_url_lines(filepath: str) -> list[str]:
    """读取 URL 文件的所有非空行（支持 # 注释）。"""
    if not os.path.isfile(filepath):
        print(f"❌ URL 文件不存在: {filepath}")
        sys.exit(1)
    lines: list[str] = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
    if not lines:
        print(f"❌ URL 文件为空: {filepath}")
        sys.exit(1)
    return lines


def build_language_filter(lang_arg: str) -> set[str] | None:
    """将语言参数解析为过滤集合。"""
    if lang_arg.lower() == "all":
        return None
    return {lang.strip() for lang in lang_arg.split(",") if lang.strip()}


def _download_one(
    url: str,
    args: argparse.Namespace,
    language_filter: set[str] | None,
    index: int = 0,
    total: int = 0,
) -> str:
    """下载单个视频的字幕，返回状态描述。"""
    prefix = f"[{index}/{total}] " if total > 1 else ""
    try:
        bvid = extract_bvid(url)
    except ValueError as exc:
        return f"{prefix}❌ {url} → {exc}"

    try:
        results = downloader.download_video_subtitles(
            bvid=bvid,
            cookie=args.cookie,
            output_dir=args.output,
            fmt=args.format,
            page_index=args.page,
            language_filter=language_filter,
        )
    except Exception as exc:
        return f"{prefix}❌ {bvid} → {exc}"

    file_count = sum(len(r.get("subtitles", [])) for r in results)
    if file_count:
        return f"{prefix}✅ {bvid} → {file_count} 个文件"
    return f"{prefix}⚠️  {bvid} → 无可用字幕"


def main(argv: list[str] | None = None) -> None:
    """命令行入口。"""
    args = parse_arguments(argv)

    # 收集 URL 列表
    if args.url_file:
        urls = _read_url_lines(args.url_file)
    elif args.url:
        urls = list(args.url)
    else:
        print("❌ 请提供视频 URL（位置参数或 --url-file）")
        sys.exit(1)

    # Cookie
    if args.cookie_file:
        args.cookie = _read_first_line(args.cookie_file, "Cookie")

    language_filter = build_language_filter(args.lang)

    total = len(urls)
    if total > 1:
        print(f"📦 共 {total} 个视频")
        print(f"输出目录: {os.path.abspath(args.output)}")
        print(f"格式: {args.format}")
        if language_filter:
            print(f"语言: {', '.join(language_filter)}")
        print()

    results: list[str] = []
    for i, url in enumerate(urls, 1):
        result = _download_one(url, args, language_filter, index=i, total=total)
        results.append(result)
        print(result)

    # 汇总
    success = sum(1 for r in results if "✅" in r)
    failed = len(results) - success
    if len(results) > 1:
        print(f"\n{'=' * 50}")
        print(f"✅ 成功: {success}  ❌ 失败: {failed}")
        print(f"📁 保存在: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()

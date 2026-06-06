"""YouTube 字幕下载工具 — 命令行入口。"""

import argparse
import os
import sys

from . import downloader

# ── 语言简写映射 ────────────────────────────────────────────────────────

_LANG_MAP: dict[str, str] = {
    "zh": "zh-Hans,zh,zh-CN,zh-TW,zh-HK",
    "en": "en",
    "fr": "fr",
    "ja": "ja",
    "ko": "ko",
    "de": "de",
    "es": "es",
    "auto": "zh-Hans,zh,zh-CN,zh-TW,zh-HK,en,fr",
}


def _resolve_language(lang_arg: str) -> str:
    """将语言选项解析为 yt-dlp 语言代码列表。"""
    return _LANG_MAP.get(lang_arg, lang_arg)


def parse_arguments(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="YouTube 视频字幕下载工具（支持多 URL 批量下载）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
快速开始:
  # 单 URL
  python3 youtube_sub.py "https://youtube.com/watch?v=..." -C cookies.txt

  # 多 URL（命令行）
  python3 youtube_sub.py "https://..." "https://..." -C cookies.txt

  # 多 URL（文件，每行一个）
  python3 youtube_sub.py -U urls.txt -C cookies.txt -P socks5://127.0.0.1:10886""",
    )
    parser.add_argument(
        "url",
        nargs="*",
        default=None,
        help="YouTube 视频 URL（可多个，与 --url-file 二选一）",
    )
    parser.add_argument(
        "-U",
        "--url-file",
        default=None,
        metavar="FILE",
        help="从文件读取视频 URL（每行一个）",
    )
    parser.add_argument(
        "-f",
        "--format",
        default="srt",
        choices=["srt", "vtt", "ass", "lrc", "txt"],
        help="输出格式 (默认: srt)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="./subtitles",
        help="输出目录 (默认: ./subtitles)",
    )
    parser.add_argument(
        "-l",
        "--lang",
        default="zh",
        help="字幕语言: zh(中文*) en(英语) fr(法语) ja(日语) ko(韩语) auto(自动) (默认: zh)",
    )
    parser.add_argument(
        "-P",
        "--proxy",
        default=None,
        metavar="URL",
        help="代理地址，如 socks5://127.0.0.1:10886",
    )
    parser.add_argument(
        "-C",
        "--cookie-file",
        default=None,
        metavar="FILE",
        help="Netscape 格式的 cookies 文件",
    )
    parser.add_argument(
        "--cookies-from-browser",
        default=None,
        metavar="BROWSER",
        choices=["chrome", "firefox", "safari", "edge", "brave", "opera"],
        help="直接从浏览器读取 cookie（需浏览器已登录）",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="仅列出可用字幕，不下载",
    )
    parser.add_argument(
        "-a",
        "--auto-only",
        action="store_true",
        help="仅下载自动生成字幕",
    )
    parser.add_argument(
        "-m",
        "--manual-only",
        action="store_true",
        help="仅下载手动上传字幕",
    )
    return parser.parse_args(argv)


def _read_lines(filepath: str) -> list[str]:
    """读取文件的所有非空行。"""
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


def _download_one(
    url: str,
    args: argparse.Namespace,
    index: int = 0,
    total: int = 0,
) -> tuple[str, bool]:
    """下载单个视频的字幕，返回 (状态描述, 是否成功)。"""
    prefix = f"[{index}/{total}] " if total > 1 else ""
    try:
        files = downloader.download_subtitles(
            url=url,
            output_dir=args.output,
            fmt=args.format,
            languages=_resolve_language(args.lang),
            auto_subs=not args.manual_only,
            manual_subs=not args.auto_only,
            cookie_file=args.cookie_file,
            cookies_from_browser=args.cookies_from_browser,
            proxy=args.proxy,
        )
        if files:
            return (f"{prefix}✅ {url} → {len(files)} 个文件", True)
        return (f"{prefix}⚠️  {url} → 无可用字幕", False)
    except Exception as exc:
        return (f"{prefix}❌ {url} → {exc}", False)


def main(argv: list[str] | None = None) -> None:
    """命令行入口。"""
    args = parse_arguments(argv)

    if args.cookie_file and args.cookies_from_browser:
        print("❌ --cookie-file 和 --cookies-from-browser 不能同时使用")
        sys.exit(1)

    # 收集 URL 列表
    if args.url_file:
        urls = _read_lines(args.url_file)
    elif args.url:
        urls = list(args.url)
    else:
        print("❌ 请提供视频 URL（位置参数或 --url-file）")
        sys.exit(1)

    # --list 模式（只对第一个 URL）
    if args.list:
        try:
            output = downloader.list_subtitles(
                urls[0],
                cookie_file=args.cookie_file,
                cookies_from_browser=args.cookies_from_browser,
                proxy=args.proxy,
            )
            print(output)
        except Exception as exc:
            print(f"❌ {exc}")
            sys.exit(1)
        return

    total = len(urls)
    if total > 1:
        print(f"📦 共 {total} 个视频\n")

    results: list[tuple[str, bool]] = []
    for i, url in enumerate(urls, 1):
        result = _download_one(url, args, index=i, total=total)
        results.append(result)
        print(result[0])

    # 汇总
    success = sum(1 for _, ok in results if ok)
    failed = len(results) - success
    if len(results) > 1:
        print(f"\n{'=' * 50}")
        print(f"✅ 成功: {success}  ❌ 失败: {failed}")
        print(f"📁 保存在: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()

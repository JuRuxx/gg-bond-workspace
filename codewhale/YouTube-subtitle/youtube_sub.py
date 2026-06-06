#!/usr/bin/env python3
"""YouTube 字幕下载 — 入口脚本。

用法:
    python3 youtube_sub.py <YouTube视频URL>
    python3 youtube_sub.py --url-file url.txt
    python3 youtube_sub.py --url-file url.txt --list
"""

from youtube_subtitle.cli import main

if __name__ == "__main__":
    main()

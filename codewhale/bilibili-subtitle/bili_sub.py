#!/usr/bin/env python3
"""向后兼容入口，实际逻辑已迁移至 bilibili_subtitle 包。

用法保持不变:
    python3 bili_sub.py <B站视频URL> -c <SESSDATA> -f srt -o ./subtitles
"""

from bilibili_subtitle.cli import main

if __name__ == "__main__":
    main()

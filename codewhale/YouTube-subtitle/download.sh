#!/bin/bash
# YouTube 字幕下载 — 一行命令快捷入口
# 用法: ./download.sh
# 需要先在 url.txt 中写入视频 URL

set -euo pipefail
cd "$(dirname "$0")"

python3 -m youtube_subtitle.cli \
    --url-file url.txt \
    "$@"

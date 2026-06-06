# youtube-subtitle
> YouTube 视频字幕下载工具

## 这是什么

youtube-subtitle 是一个从 YouTube 视频下载字幕的命令行工具。
基于 Python + yt-dlp，支持自动生成字幕和手动上传字幕，导出为 SRT / VTT / ASS 等格式。
自动按「中文 > 英文 > 其他」优先级选择最佳字幕，只保留一个文件。

## 快速开始

```bash
# 1. 安装依赖
pip install yt-dlp

# 2. 导出 cookies（仅需一次，用于绕过网络限制）
yt-dlp --cookies-from-browser chrome --cookies cookies.txt \
    --print id --skip-download "https://www.youtube.com/watch?v=..."

# 3. 写入视频 URL
echo "https://www.youtube.com/watch?v=..." > url.txt

# 4. 下载
python3 youtube_sub.py --url-file url.txt --cookie-file cookies.txt
```

字幕文件默认输出到 `./subtitles/`。

### 用法

```bash
# 基础用法
python3 youtube_sub.py --url-file url.txt --cookie-file cookies.txt

# 带代理（中国大陆用户）
python3 youtube_sub.py --url-file url.txt --cookie-file cookies.txt -P socks5://127.0.0.1:10886

# 命令行直传
python3 youtube_sub.py "https://www.youtube.com/watch?v=..."

# 查看可用字幕
python3 youtube_sub.py --url-file url.txt --cookie-file cookies.txt --list

# 快捷脚本
./download.sh
```

### 完整参数

```
python3 youtube_sub.py [url] [选项]

  url                       视频 URL（位置参数）
  -U, --url-file FILE        从文件读取 URL
  -f, --format FMT           输出格式: srt / vtt / ass / lrc / txt（默认 srt）
  -o, --output DIR           输出目录（默认 ./subtitles）
  -l, --lang LANG            字幕语言: zh / en / fr / ja / ko / auto（默认 zh）
  -P, --proxy URL            代理地址，如 socks5://127.0.0.1:10886
  -C, --cookie-file FILE     Netscape cookies 文件
  --cookies-from-browser BROWSER  从浏览器读取 cookie (chrome/firefox/safari)
  --list                     仅列出可用字幕
  -a, --auto-only            仅下载自动生成字幕
  -m, --manual-only          仅下载手动上传字幕
```

### 语言选项

| 选项 | 说明 |
|------|------|
| `zh`（默认） | 中文（zh-Hans, zh-CN, zh-TW, zh-HK） |
| `en` | 英语 |
| `fr` | 法语 |
| `ja` | 日语 |
| `ko` | 韩语 |
| `auto` | 自动（中文 > 英文 > 法语） |

也可直接传语言代码：`-l zh-Hans` 或 `-l en,fr`。yt-dlp 尝试所有匹配语言，最终只保留优先级最高的一个文件。

手动指定单一语言：

```bash
python3 youtube_sub.py -U url.txt -C cookies.txt -l ja    # 只下载日文
```

## 配置

| 文件 | 说明 | 必填 |
|------|------|------|
| `url.txt` | 视频 URL，取文件第一行 | 是 |
| `cookies.txt` | Netscape 格式 cookies（`yt-dlp --cookies` 导出） | 推荐 |

`url.txt` 和 `cookies.txt` 已在 `.gitignore` 中，不会被提交到仓库。

## 目录结构

```
YouTube-subtitle/
├── youtube_sub.py              # 入口脚本
├── download.sh                 # 快捷脚本
├── youtube_subtitle/           # 核心包
│   ├── cli.py                  #   命令行入口
│   └── downloader.py           #   yt-dlp 调用封装
├── url.txt                     # 视频 URL（gitignore）
├── cookies.txt                 # 浏览器 cookies（gitignore）
├── subtitles/                  # 字幕输出目录
└── SKILL.md                    # CodeWhale Agent 技能定义
```

## 开发

```bash
pip install yt-dlp
python3 -m youtube_subtitle.cli --help
python3 youtube_sub.py "https://www.youtube.com/watch?v=..." --list -C cookies.txt
```

## FAQ

**Q: 下载报 429 / 403？**
三步解决：
1. 换代理节点：`-P socks5://127.0.0.1:10886`
2. 带 cookie：`--cookie-file cookies.txt`
3. 等 5-10 分钟冷却

**Q: 怎么导出 cookies？**
```bash
yt-dlp --cookies-from-browser chrome --cookies cookies.txt --print id --skip-download "https://www.youtube.com/watch?v=..."
```

**Q: 同时下载中英文？**
传 `-l zh-Hans,en` 会下载匹配的所有语言，自动保留优先级最高的。如需保留全部，直接检查 `./subtitles/` 目录。

## LICENSE

MIT

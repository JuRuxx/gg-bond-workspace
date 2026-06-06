# bilibili-subtitle
> B 站视频字幕下载工具

## 这是什么

bilibili-subtitle 是一个从 B 站视频下载字幕的命令行工具。
基于 Python + requests，调用 B 站 API 获取字幕列表并导出为 SRT / TXT / JSON 格式。
适用于字幕翻译、语料收集、内容检索等场景。

## 快速开始

```bash
# 1. 安装依赖
pip install requests

# 2. 写入配置（仅需一次）
echo "https://www.bilibili.com/video/BV..." > url.txt
echo "你的SESSDATA" > sessdata.txt

# 3. 下载
python3 bili_sub.py --url-file url.txt --cookie-file sessdata.txt
```

字幕文件默认输出到 `./subtitles/`。

### 用法

```bash
# 配置文件方式（推荐，一行命令）
python3 bili_sub.py --url-file url.txt --cookie-file sessdata.txt

# 命令行方式
python3 bili_sub.py "https://www.bilibili.com/video/BV..." -c "你的SESSDATA"

# 快捷脚本
./download.sh
```

### 完整参数

```
python3 bili_sub.py [url] [选项]

  url                    视频 URL 或 BVID
  -U, --url-file FILE     从文件读取 URL
  -c, --cookie COOKIE     SESSDATA cookie
  -C, --cookie-file FILE  从文件读取 SESSDATA
  -f, --format FMT        输出格式: srt / txt / json / all（默认 srt）
  -o, --output DIR        输出目录（默认 ./subtitles）
  -p, --page N            指定分 P（默认全部）
  -l, --lang LANG         语言: zh / en / ja / ...（默认 zh）
```

### 示例

```bash
# JSON 格式，第 2 个分 P，中英双语
python3 bili_sub.py -U url.txt -C sessdata.txt -f json -p 2 -l zh,en

# 下载全部语言
python3 bili_sub.py -U url.txt -C sessdata.txt -l all
```

## 配置

| 文件 | 说明 | 必填 |
|------|------|------|
| `url.txt` | 视频 URL，取文件第一行 | 是 |
| `sessdata.txt` | B 站登录态 Cookie，取文件第一行 | 是（大部分视频需要） |

获取 SESSDATA：浏览器登录 [bilibili.com](https://www.bilibili.com) → F12 → Application → Cookies → `bilibili.com` → `SESSDATA`。
有效期约 30 天，过期后需重新获取。

`url.txt` 和 `sessdata.txt` 已在 `.gitignore` 中，不会被提交到仓库。

## 目录结构

```
bilibili-subtitle/
├── bili_sub.py                 # 入口脚本
├── download.sh                 # 快捷脚本
├── bilibili_subtitle/          # 核心包
│   ├── cli.py                  #   命令行入口
│   ├── downloader.py           #   下载流程编排
│   ├── api.py                  #   HTTP 客户端
│   ├── bvid.py                 #   BVID ↔ AID 转换
│   ├── signing.py              #   WBI 签名
│   └── export.py               #   格式转换 (SRT/TXT/JSON)
├── url.txt                     # 视频 URL（gitignore）
├── sessdata.txt                # SESSDATA cookie（gitignore）
├── subtitles/                  # 字幕输出目录
└── SKILL.md                    # CodeWhale Agent 技能定义
```

## 开发

```bash
# 安装依赖
pip install requests

# 验证环境
python3 -m bilibili_subtitle.cli --help

# 模块级测试
python3 -c "from bilibili_subtitle.bvid import bvid_to_aid, aid_to_bvid; assert aid_to_bvid(bvid_to_aid('FVxxx...')) == 'FVxxx...'"
```

## FAQ

**Q: 为什么下载不到字幕？**
大部分 B 站视频需要登录态才能获取字幕列表，请确认 `sessdata.txt` 中的 SESSDATA 有效且未过期。

**Q: 字幕质量如何？**
B 站 AI 自动生成字幕（`lan=ai-zh`）可能有术语误识别，人工上传的字幕质量更高。

## LICENSE

MIT

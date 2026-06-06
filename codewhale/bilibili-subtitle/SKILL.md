---
name: "bilibili-subtitle-download"
description: "下载 B站视频字幕，导出为 SRT/TXT/JSON 格式。支持配置文件方式一行命令下载。"
---

# B站字幕下载

## 执行流程

### 1. 确认配置

检查当前目录下是否存在 `url.txt` 和 `sessdata.txt`。

- 如果存在，读取第一行作为 URL 和 SESSDATA，跳至步骤 3
- 如果缺失，进入步骤 2

### 2. 收集用户输入

按顺序向用户索要以下信息，**每个步骤单独询问，等用户回复后再问下一个**：

1. **视频 URL** — 用户提供 B站视频链接或 BVID，写入 `url.txt`
2. **SESSDATA cookie** — 如果用户不知道如何获取，解释：浏览器登录 bilibili.com → F12 → Application → Cookies → bilibili.com → SESSDATA，复制值，写入 `sessdata.txt`
3. **输出格式** — srt / txt / json / all，默认 srt（用户不选就是 srt）
4. **分 P** — 全部还是指定某 P，默认全部

### 3. 获取视频信息并告知用户

运行以下命令获取视频信息（仅获取信息，不下载字幕）：

```bash
python3 -c "
from bilibili_subtitle.api import fetch_video_info
from bilibili_subtitle.signing import fetch_mixin_key
info = fetch_video_info('$(head -1 url.txt)', fetch_mixin_key())
print(f'标题: {info[\"title\"]}')
print(f'分P数: {len(info.get(\"pages\", []))}')
for i, p in enumerate(info.get('pages', []), 1):
    print(f'  P{i}: {p.get(\"part\", \"无标题\")}')
"
```

告知用户视频标题和分 P 信息。如果视频有多个分 P 且用户选的是「全部」，确认是否继续。

### 4. 下载字幕

```bash
python3 bili_sub.py --url-file url.txt --cookie-file sessdata.txt \
    -f <用户选择的格式> \
    -p <用户选择的分P，全部则不传 -p> \
    -l <用户选择的语言，默认 zh>
```

### 5. 确认结果

列出 `./subtitles/` 目录下生成的文件，告知用户文件数量和路径。

### 6. 清理（询问）

询问用户是否需要将字幕文件移动到其他位置（`./subtitles/` 是临时目录）。

## Agent 交互规则

- **一次只问一个问题**：不要在一个消息里同时索要 URL、Cookie、格式、分 P。按步骤逐一询问。
- **默认值先行**：格式默认 srt，分 P 默认全部，语言默认 zh。用户不选就跳过那步。
- **Cookie 引导**：如果用户不知道 SESSDATA 是什么，提供获取步骤。
- **空字幕处理**：如果某个分 P 无字幕，告知用户并继续处理其他分 P。
- **错误处理**：API 报错时告知用户具体错误信息，不要静默跳过。
- **频繁请求警告**：连续下载多个视频时，每次间隔 3-5 秒。

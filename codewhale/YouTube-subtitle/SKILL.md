---
name: "youtube-subtitle-download"
description: "获取YouTube视频字幕。当用户发送YouTube视频链接时触发此技能。下载字幕为SRT格式，按中文>英文优先级选择最佳语言。"
---

# YouTube 字幕下载

## 触发条件

当用户提供以下内容时激活：
- YouTube 视频链接（youtube.com / youtu.be）
- 明确提到 "YouTube"、"油管"
- 要求获取 YouTube 视频字幕

## 执行流程

### 1. 确认配置

检查 `url.txt` 和 `cookies.txt` 是否存在。
- `url.txt` 缺失 → 让用户提供 URL 并写入
- `cookies.txt` 缺失 → 引导用户导出：Chrome 登录 youtube.com → 运行 `yt-dlp --cookies-from-browser chrome --cookies cookies.txt --print id --skip-download "<任意Youtube链接>"`

### 2. 写入 URL

用户提供 URL → 写入 `url.txt`。

### 3. 查看视频信息

```bash
python3 youtube_sub.py --url-file url.txt --cookie-file cookies.txt --list
```

展示可用字幕语言给用户确认。

### 4. 下载字幕

```bash
python3 youtube_sub.py --url-file url.txt --cookie-file cookies.txt [-P socks5://127.0.0.1:10886]
```

默认语言优先级：zh-Hans > zh > zh-CN > zh-TW > zh-HK > en > fr。
只保留一个最佳匹配文件。

- 仅自动字幕：加 `-a`
- 仅手动字幕：加 `-m`
- 代理：加 `-P socks5://127.0.0.1:10886`

### 5. 确认结果

告知用户字幕文件路径。

## Agent 交互规则

- **下载前先 --list**：确认有哪些语言可用，避免白费请求
- **中文优先**：默认只下载最佳语言（中文 > 英文 > 其他），不下载多语言文件
- **Cookie 引导**：优先用 `--cookie-file cookies.txt`，`--cookies-from-browser` 在 macOS subprocess 中有钥匙串权限问题
- **代理提示**：如果用户在中国大陆，询问是否需要 `-P socks5://127.0.0.1:10886`
- **429 处理**：
  1. 提示等待 5-10 分钟
  2. 建议切换代理节点
  3. 检查 cookies.txt 是否有效

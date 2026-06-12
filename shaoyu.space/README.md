# 🌐 shaoyu.space 网站

个人网站 `https://shaoyu.space:18888` 的完整项目。

> 这里包含了**网站的所有文件 + 项目文档**，更新网站内容就是动这个文件夹。

## 📁 目录结构

```
novel-web/                    ← 📌 这就是你网站的根目录
├── README.md                 ← 本文档
├── Caddyfile                 ← Caddy Web服务器配置文件
├── caddy.log                 ← Caddy运行日志
├── server.crt                ← HTTPS自签证书
├── server.key                ← HTTPS自签证书私钥
│
├── index.html                ← 🏠 网站首页/入口
│
├── novel/                    ← 📖 小说阅读模块
│   ├── index.html            ← 小说列表页
│   ├── reader.html           ← 小说阅读器（翻页/目录）
│   ├── 第01章-第17次面试.html
│   ├── 第02章-欢迎来到加班管理局.html
│   ├── 第03章-第一个案件.html
│   …（共15章）
│   └── 第15章-加班结束了.html
│
├── engine/                   ← 🚀 火箭发动机技术研究
│   ├── 01-框架.md
│   ├── 02-燃料路线三巨头.md
│   …（共7篇）
│   └── 07-投资视角与结论.md
│
├── engine-reader.html        ← 🚀 发动机文章阅读器
│
├── tianbing-reader.html      ← 📈 天兵科技报告阅读器
├── tianbing-report.md        ← 天兵科技报告（Markdown版）
├── 天兵科技投资分析报告.md    ← 投资分析报告原文
├── 天兵科技投资分析报告.pdf  ← PDF版（可下载）
└── 天兵科技投资分析报告(精).pdf ← 精装PDF
```

## 📋 部署信息

| 项目 | 内容 |
|------|------|
| **域名** | `shaoyu.space` |
| **访问地址** | `https://shaoyu.space:18888` |
| **服务器** | 本地 Mac mini |
| **Web 服务** | Caddy v2.11.3（开机自启 ✅） |
| **隧道** | SakuraFrp（樱花节点 59.36.97.218） |
| **SSL** | 自签证书 |

## 🛠️ 如何更新网站内容

| 我想… | 怎么做 |
|-------|--------|
| **加一章小说** | 新建 `novel/第16章-xxx.html`，更新 `novel/index.html` 的目录 |
| **加一个新页面** | 直接新建 `.html` 文件，Caddy自动识别 |
| **换首页** | 修改 `index.html` |
| **更新报告** | 替换对应的 `.md` 或 `.pdf` 文件 |
| **改端口/域名** | 修改 `Caddyfile`，然后 `launchctl restart` |

## 📦 相关仓库

- `主页项目/` — 项目的PRD、技术规格、验收报告（与本文档互为补充）
- `frpc/` — SakuraFrp 隧道配置文件

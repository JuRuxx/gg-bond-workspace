# SKILL 标准

> **Skill = Tool 之上的决策层。**
>
> CodeWhale Constitution 附属文档 · 独立版本迭代 · 当前版本 2.1

---

## 核心原则

Skill 不是工具说明书。

CodeWhale 的四层结构中：

| 层级 | 回答的问题 | 示例 |
| --- | --- | --- |
| Constitution | 什么最重要（Priority） | 人类时间高于机器时间 |
| Workflow | 为什么这样做、前后依赖（Why） | TPS 标准作业书 |
| **Skill** | **什么时候做、缺什么、出错怎么办（When / Need / Fallback）** | **决策层** |
| Tool | 怎么做（How） | `download_subtitle()` |

如果一个 Skill 只是顺序调用几个工具，它应该被删除，并下沉为 Tool。

### 硬性规定

Skill 必须包含至少一个决策元语：

- `IF` — 条件判断
- `ELSE` — 二路分支
- `ASK` — 向用户主动询问
- `RETRY` — 失败重试
- `FALLBACK` — 降级方案
- `STATE TRANSITION` — 状态间切换

不含上述任何一项的 Skill，不应定义为 Skill。

---

## 标准结构

```markdown
# <技能名称>

> 版本 <语义化版本> | <一句话描述触发场景>

## 本技能回答的问题

用户什么时候会找我、我需要什么、我能调哪些工具。

### 触发场景

[用户什么场景下会调用我]

关键词：[触发词, 列表]

---

## Inputs

### 必需

- `video_url` : string — 视频页面 URL
- ...

### 可选

- `output_format` : string — 字幕输出格式（默认 srt）
- ...

---

## Tools

本技能可调用的工具列表：

- `download_subtitle()`
- `validate_subtitle()`

---

## States

> Skill 本质上是一棵决策树，每一次状态转换回答"接下来该做什么"。

```text
start
  │
  ├─ video_url 缺失 ──→ ask user ──→ got url
  │
  ├─ cookie 缺失 ──→ try anonymous
  │                     │
  │                     ├─ success ──→ proceed
  │                     └─ fail ──→ ask user for cookie ──→ got cookie
  │
  ├─ 多 P 视频 ──→ ask user for P number or all
  │
  └─ ready ──→ download
```

### 状态转换规则

每条规则 = 条件判断 + 下一步动作。

```
IF video_url missing
→ ask user for URL

IF cookie missing
→ try anonymous mode
    IF success → proceed
    IF fail → ask user for cookie

IF multi-P video
→ ask user: single P or all

IF network timeout
→ retry up to 3 times
    IF still fail → abort with error
```

---

## Success

可验证的成功标准：

- 字幕文件生成并存在于输出目录
- 文件格式与指定格式一致
- 文件内容非空

---

## Failure

已知失败场景与恢复策略：

- 视频无字幕 → 告知用户
- 字幕内容为空 → 重试一次，仍空则告知
- Cookie 失效 → 告知用户重新获取
- 网络异常 → 重试 3 次，仍失败则中止并报错

---

## 最终验收

查看一个 SKILL.md 时，只问一个问题：

> 删掉它以后，Agent 失去的是**动作**，还是**决策**？

- **如果失去的是动作** → 它应该下沉为 Tool
- **如果失去的是决策** → 它是合格的 Skill

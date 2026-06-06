"""YouTube 字幕下载核心：调用 yt-dlp 获取并下载字幕。"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


# ── 常量 ────────────────────────────────────────────────────────────────────

_DEFAULT_LANGUAGES = "zh-Hans,zh,zh-CN,zh-TW,zh-HK"

# 语言优先级：从文件名匹配时按此顺序选择
_LANG_PRIORITY = ["zh-Hans", "zh-CN", "zh-TW", "zh-HK", "zh", "en", "fr"]


# ── 运行时检测 ─────────────────────────────────────────────────────────────

def _find_deno() -> str | None:
    """查找 deno 可执行文件路径。"""
    found = shutil.which("deno")
    if found:
        return found
    candidates = [
        Path.home() / ".deno" / "bin" / "deno",
        Path("/usr/local/bin/deno"),
        Path("/opt/homebrew/bin/deno"),
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def _build_env() -> dict[str, str]:
    """构建 subprocess 环境变量，确保 yt-dlp 能找到 deno。"""
    env = os.environ.copy()
    deno_path = _find_deno()
    if deno_path:
        deno_dir = str(Path(deno_path).parent)
        existing_path = env.get("PATH", "")
        if deno_dir not in existing_path:
            env["PATH"] = f"{deno_dir}:{existing_path}"
    return env


def ensure_yt_dlp() -> None:
    """检查 yt-dlp 是否已安装，未安装则提示并退出。"""
    try:
        subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            check=True,
            env=_build_env(),
        )
    except FileNotFoundError:
        print("❌ 未找到 yt-dlp。请先安装: pip install yt-dlp")
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("❌ yt-dlp 运行异常，请重新安装: pip install --upgrade yt-dlp")
        sys.exit(1)


# ── 内部辅助 ────────────────────────────────────────────────────────────────

def _build_yt_dlp_cmd(
    *,
    proxy: str | None = None,
    cookie_file: str | None = None,
    cookies_from_browser: str | None = None,
) -> list[str]:
    """构建 yt-dlp 基础命令，附加公共参数。"""
    cmd = ["yt-dlp", "--js-runtimes", "deno"]
    if proxy:
        cmd.extend(["--proxy", proxy])
    if cookie_file:
        cmd.extend(["--cookies", cookie_file])
    elif cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])
    return cmd


# ── 公开 API ────────────────────────────────────────────────────────────────

def list_subtitles(
    url: str,
    *,
    cookie_file: str | None = None,
    cookies_from_browser: str | None = None,
    proxy: str | None = None,
) -> str:
    """列出视频的可用字幕语言。"""
    ensure_yt_dlp()
    cmd = _build_yt_dlp_cmd(
        proxy=proxy,
        cookie_file=cookie_file,
        cookies_from_browser=cookies_from_browser,
    )
    cmd.extend(["--list-subs", url])

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=90, env=_build_env()
    )
    output = result.stdout.strip()
    if not output:
        raise RuntimeError(f"获取字幕列表失败: {result.stderr.strip()}")
    return output


def fetch_video_meta(
    url: str,
    *,
    cookie_file: str | None = None,
    cookies_from_browser: str | None = None,
    proxy: str | None = None,
) -> dict[str, str]:
    """获取视频元数据：标题、频道、时长。"""
    ensure_yt_dlp()
    cmd = _build_yt_dlp_cmd(
        proxy=proxy,
        cookie_file=cookie_file,
        cookies_from_browser=cookies_from_browser,
    )
    cmd.extend([
        "--skip-download",
        "--print", "%(title)s|||%(uploader)s|||%(duration_string)s",
        url,
    ])

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120, env=_build_env()
    )
    output = result.stdout.strip()
    if result.returncode != 0 or not output or "|||" not in output:
        return {"title": url, "uploader": "", "duration": ""}

    parts = output.split("|||", 2)
    return {
        "title": parts[0].strip() if len(parts) > 0 else url,
        "uploader": parts[1].strip() if len(parts) > 1 else "",
        "duration": parts[2].strip() if len(parts) > 2 else "",
    }


def download_subtitles(
    url: str,
    output_dir: str = "./subtitles",
    fmt: str = "srt",
    languages: str = _DEFAULT_LANGUAGES,
    auto_subs: bool = True,
    manual_subs: bool = True,
    *,
    cookie_file: str | None = None,
    cookies_from_browser: str | None = None,
    proxy: str | None = None,
) -> list[str]:
    """下载视频字幕到指定目录。

    Args:
        url: YouTube 视频 URL。
        output_dir: 输出目录路径。
        fmt: 输出格式。
        languages: 逗号分隔的语言代码。
        auto_subs: 是否下载自动生成字幕。
        manual_subs: 是否下载手动上传字幕。
        cookie_file: Netscape 格式的 cookies 文件路径。
        cookies_from_browser: 从指定浏览器读取 cookie。
        proxy: 代理地址，如 socks5://127.0.0.1:10886。

    Returns:
        下载的字幕文件路径列表。
    """
    ensure_yt_dlp()
    env = _build_env()

    # ── 展示视频信息 ────────────────────────────────────────────────────
    try:
        meta = fetch_video_meta(
            url,
            cookie_file=cookie_file,
            cookies_from_browser=cookies_from_browser,
            proxy=proxy,
        )
        print("🎬 视频信息")
        print(f"   标题: {meta['title']}")
        if meta["uploader"]:
            print(f"   频道: {meta['uploader']}")
        if meta["duration"]:
            print(f"   时长: {meta['duration']}")
        print(f"   链接: {url}")
        print()
    except Exception as exc:
        print(f"⚠️  无法获取视频信息 ({exc})，继续下载字幕...")
        print()

    os.makedirs(output_dir, exist_ok=True)
    before: set[str] = set(os.listdir(output_dir))

    cmd = _build_yt_dlp_cmd(
        proxy=proxy,
        cookie_file=cookie_file,
        cookies_from_browser=cookies_from_browser,
    )
    cmd.extend([
        "--skip-download",
        "--sub-langs", languages,
        "--sub-format", f"{fmt}/best",
        "-o", f"{output_dir}/%(title)s [%(id)s].%(ext)s",
        "--remote-components", "ejs:github",
        "--sleep-requests", "5",
        "--sleep-interval", "5",
        "--max-sleep-interval", "12",
    ])

    if auto_subs:
        cmd.append("--write-auto-subs")
    if manual_subs:
        cmd.append("--write-subs")
    if not auto_subs and not manual_subs:
        cmd.append("--write-auto-subs")

    cmd.append(url)

    print(f"📥 下载字幕")
    print(f"   语言: {languages}")
    print(f"   格式: {fmt}")
    print(f"   输出: {output_dir}/")
    if cookie_file:
        print(f"   Cookie: {cookie_file}")
    elif cookies_from_browser:
        print(f"   Cookie: 浏览器 ({cookies_from_browser})")
    if proxy:
        print(f"   代理: {proxy}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)

    after: set[str] = set(os.listdir(output_dir))
    new_files = sorted(after - before)

    if result.returncode != 0 and not new_files:
        error_msg = result.stderr.strip() or result.stdout.strip()
        for line in reversed((result.stderr + "\n" + result.stdout).splitlines()):
            line = line.strip()
            if line and not line.startswith("WARNING"):
                if "429" in line:
                    error_msg = (
                        "YouTube 请求过于频繁 (HTTP 429)。\n"
                        "  1. 等待 5-10 分钟后重试\n"
                        "  2. 如果使用代理/VPN，尝试切换节点\n"
                        "  3. 使用 --cookie-file cookies.txt 提供登录态\n"
                        f"原始错误: {line}"
                    )
                elif "403" in line:
                    error_msg = (
                        "YouTube 拒绝访问 (HTTP 403)。\n"
                        "  尝试使用 --cookie-file cookies.txt 提供登录态\n"
                        f"原始错误: {line}"
                    )
                break
        raise RuntimeError(f"字幕下载失败: {error_msg}")

    # 按语言优先级只保留最佳匹配
    new_files = _pick_best_lang(new_files)
    return [os.path.join(output_dir, f) for f in new_files]


def _pick_best_lang(files: list[str]) -> list[str]:
    """从文件列表中按语言优先级只保留最佳匹配。"""
    files = [f for f in files if os.path.splitext(f)[1] in (".srt", ".vtt", ".ass", ".lrc", ".txt")]
    if len(files) <= 1:
        return files

    for preferred in _LANG_PRIORITY:
        for f in files:
            basename = os.path.basename(f)
            # 文件名格式: {title} [{id}].{lang}.{ext}
            parts = basename.rsplit(".", 2)
            if len(parts) >= 2 and parts[-2] == preferred:
                # 删除其他语言文件，只保留这个
                for other in files:
                    if other != f:
                        os.remove(other)
                return [f]
    return files

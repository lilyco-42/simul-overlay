# -*- coding: utf-8 -*-
"""翻译引擎层：本地翻译为主 + API 可选（原始决策的落地）。

离线路径（默认，完全无网络——除非按需下载语对包）：
  1. 直连语对存在 → 直接翻
  2. 缺直连 → 英语 pivot 两跳路由（Argos 语对结构即"各语种↔en"）
  3. 语对包缺失 → ensure_pair() 自动下载安装（仅首次）

API 路径（可选，用户自填，OpenAI 兼容）：
  SIMUL_API_BASE   如 https://api.example.com/v1
  SIMUL_API_KEY    key
  SIMUL_API_MODEL  如 gpt-4o-mini / qwen-plus / deepseek-chat
  SIMUL_FORCE_OFFLINE=1 强制离线（即使配了 key）
"""
import json
import os
import re
import threading
import urllib.request

from argostranslate import package, settings, translate as argos

_lock = threading.RLock()  # ensure_pair 在持锁内会再调 installed_pairs()，必须可重入
_pairs = None  # set[(from,to)] 已安装语对缓存

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# NMT 退化重复（如 "Good morning" → "早,早,早…"）：片段(≤12字,无句读) + 分隔(句读/空白) + 同片段 ≥1 次
_REPEAT = re.compile(r"([^\s,，。！？；;.!?]{1,12})(?:[,，。！？；;.!\s]+\1){1,}")


def _collapse_repeats(s):
    """清洗翻译输出的机械重复（逗号/句号/空白分隔的完全相同片段）。"""
    prev = None
    while prev != s:
        prev = s
        s = _REPEAT.sub(r"\1", s)
    return s.strip()


def _download_pkg(pkg):
    """带浏览器 UA 下载语对包（绕坑专用）。

    argos-net.com 对 Python 默认 UA 返回 403，Argos 内置 pkg.download()
    随后回落 ipfs:// 链接无限挂起。这里只走 https 链接 + 浏览器 UA + 超时。
    """
    fname = f"translate-{pkg.from_code}_{pkg.to_code}-{pkg.package_version}.argosmodel"
    print(f"[dl] start {fname} ...", flush=True)
    dest = settings.downloads_dir / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return str(dest)
    errs = []
    for url in [u for u in pkg.links if u.startswith("http")]:
        try:
            req = urllib.request.Request(url, headers=_UA)
            tmp = dest.with_suffix(".part")
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            tmp.replace(dest)
            return str(dest)
        except Exception as e:  # 尝试下一条 https 链接
            errs.append(f"{url}: {e}")
    raise RuntimeError("语对包下载失败: " + "; ".join(errs))


def installed_pairs():
    global _pairs
    with _lock:
        if _pairs is None:
            _pairs = {(p.from_code, p.to_code) for p in package.get_installed_packages()}
    return _pairs


def available_pairs():
    return {(p.from_code, p.to_code): p for p in package.get_available_packages()}


def ensure_pair(src, dst):
    """按需下载安装语对包（仅首次）。成功返回 True。"""
    if (src, dst) in installed_pairs():
        return True
    pkg = available_pairs().get((src, dst))
    if pkg is None:
        try:  # 本地索引可能过期 → 刷新一次再查
            package.update_package_index()
        except Exception:
            pass
        pkg = available_pairs().get((src, dst))
    if pkg is None:
        return False
    with _lock:
        if (src, dst) in installed_pairs():  # 双检，防并发重复装
            return True
        path = _download_pkg(pkg)
        package.install_from_path(path)
        installed_pairs().add((src, dst))
    return True


def detect_lang(text):
    """基于文字系统的语种检测（脚本优先 + 少量停用词兜底）。"""
    if re.search(r"[\u3040-\u30ff]", text):          # 平假名/片假名 → 日语
        return "ja"
    if re.search(r"[\uac00-\ud7af]", text):          # 谚文 → 韩语
        return "ko"
    if re.search(r"[\u0600-\u06ff]", text):          # 阿拉伯文
        return "ar"
    if re.search(r"[\u0e00-\u0e7f]", text):          # 泰文
        return "th"
    if re.search(r"[\u0400-\u04ff]", text):          # 西里尔 → 俄语等
        return "ru"
    has_han = bool(re.search(r"[\u4e00-\u9fff]", text))
    latin = re.sub(r"[^A-Za-z]", "", text)
    if has_han:
        return "zh"
    if not latin:
        return "zh" if has_han else "en"
    # 拉丁字母语种：停用词嗅探（法/德/西/葡/意）
    low = " " + text.lower() + " "
    if any(w in low for w in (" le ", " les ", " des ", " une ", " est ")):
        return "fr"
    if any(w in low for w in (" der ", " die ", " das ", " ist ", " nicht ")):
        return "de"
    if any(w in low for w in (" el ", " los ", " las ", " que ", " una ")):
        return "es"
    if any(w in low for w in (" o ", " os ", " uma ", " não ", " que ")):
        return "pt"
    if any(w in low for w in (" il ", " lo ", " che ", " una ", " non ")):
        return "it"
    accented = re.sub(r"[A-Za-z\s]", "", text)
    if accented and re.search(r"[À-ÿ]", accented):
        return "fr"  # 带重音拉丁兜底
    return "en"


def offline_translate(text, src, dst):
    """离线翻译：直连 → pivot 两跳 → 按需装包 → 仍失败返回 None。"""
    pairs = installed_pairs()
    if (src, dst) in pairs:
        return argos.translate(text, src, dst)
    # pivot：src→en + en→dst（按需装包）
    if src != "en" and dst != "en":
        if ensure_pair(src, "en") and ensure_pair("en", dst):
            mid = argos.translate(text, src, "en")
            return argos.translate(mid, "en", dst)
    # 单跳缺包：按需装直连
    if ensure_pair(src, dst):
        return argos.translate(text, src, dst)
    return None


def api_translate(text, src, dst):
    """OpenAI 兼容 Chat Completions（用户自填 key，可选路径）。"""
    base = os.environ.get("SIMUL_API_BASE", "").rstrip("/")
    key = os.environ.get("SIMUL_API_KEY", "")
    model = os.environ.get("SIMUL_API_MODEL", "gpt-4o-mini")
    if not base or not key:
        return None
    body = json.dumps({
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system",
             "content": f"Translate from {src} to {dst}. Output only the translation."},
            {"role": "user", "content": text},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def translate(text, src=None, dst=None):
    """统一入口：默认离线；配了 API key 且未强制离线时走 API，失败回落离线。"""
    src = src or detect_lang(text)
    if src == dst:
        return text
    dst = dst or ("en" if src == "zh" else "zh")
    dst = os.environ.get("SIMUL_TARGET_LANG") or dst  # 显式目标语种开关（如恒翻中文: zh）

    if os.environ.get("SIMUL_FORCE_OFFLINE") != "1":
        try:
            out = api_translate(text, src, dst)
            if out:
                return _collapse_repeats(out)
        except Exception:
            pass  # API 不可用 → 回落离线，字幕永不阻塞
    out = offline_translate(text, src, dst)
    if out is not None:
        return _collapse_repeats(out)
    return f"[本地缺语对 {src}→{dst}，可设置 SIMUL_API_* 或重跑以自动装包]"

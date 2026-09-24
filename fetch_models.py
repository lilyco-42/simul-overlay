# -*- coding: utf-8 -*-
"""拉取桌面离线全量包所需模型 + 核心 6 语对（幂等；本地与 CI 通用）。

产出布局（models/，已 gitignore）：
  sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20/   ASR int8 四件套
  silero_vad.onnx                                                VAD
  tts/kokoro-multi-lang-v1_0/                                    TTS kokoro 全套
  argos-packages/                                                zh/ja/ko ↔ en 六对（682MB）

用法: python fetch_models.py
"""
import os
import shutil
import sys
import tarfile
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(ROOT, "models")
CACHE = os.path.join(MODELS, ".cache")

# 语对装进随包目录（必须在 import translate_engine 之前设好，settings 读 env 优先）
ARGOS_DIR = os.path.join(MODELS, "argos-packages")
os.environ.setdefault("ARGOS_PACKAGES_DIR", ARGOS_DIR)

ASR_NAME = "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"
TTS_NAME = "kokoro-multi-lang-v1_0"
GH = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
ASR_URL = f"{GH}/asr-models/{ASR_NAME}.tar.bz2"
VAD_URL = f"{GH}/asr-models/silero_vad.onnx"  # 注意：挂在 asr-models 下，非 vad-models
TTS_URL = f"{GH}/tts-models/{TTS_NAME}.tar.bz2"

# 桌面 pipeline.build_recognizer 实际加载的 4 个文件（int8 encoder/decoder/joiner + tokens；
# 与 Android 的 fp32 decoder 不同，勿混）。全量 tar 531MB，prune 后 ~100MB。
ASR_KEEP = {
    "tokens.txt",
    "encoder-epoch-99-avg-1.int8.onnx",
    "decoder-epoch-99-avg-1.int8.onnx",
    "joiner-epoch-99-avg-1.int8.onnx",
}

# M4 首发核心语对：zh/ja/ko ↔ en（其余语对留 ensure_pair 联网补装）
ARGOS_PAIRS = [
    ("zh", "en"), ("en", "zh"),
    ("ja", "en"), ("en", "ja"),
    ("ko", "en"), ("en", "ko"),
]


def _download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"[fetch] {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    part = dest + ".part"
    with urllib.request.urlopen(req, timeout=600) as r, open(part, "wb") as f:
        total = 0
        last = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if total - last >= 50 << 20:
                print(f"[fetch]   {total // (1 << 20)} MB", flush=True)
                last = total
    os.replace(part, dest)
    print(f"[fetch] done {os.path.getsize(dest) // (1 << 20)} MB", flush=True)


def _extract_tarbz2(archive, dest_dir):
    print(f"[fetch] extracting {os.path.basename(archive)} ...", flush=True)
    with tarfile.open(archive, "r:bz2") as tar:
        try:
            tar.extractall(dest_dir, filter="data")
        except TypeError:  # Python < 3.12 无 filter 参数
            tar.extractall(dest_dir)


def ensure_asr():
    dest = os.path.join(MODELS, ASR_NAME)
    if os.path.exists(os.path.join(dest, "tokens.txt")):
        return
    archive = os.path.join(CACHE, ASR_NAME + ".tar.bz2")
    _download(ASR_URL, archive)
    _extract_tarbz2(archive, CACHE)
    src = os.path.join(CACHE, ASR_NAME)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.move(src, dest)
    for name in os.listdir(dest):  # prune 只留运行时 4 文件
        if name in ASR_KEEP:
            continue
        p = os.path.join(dest, name)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            os.remove(p)
    print(f"[fetch] ASR -> {dest} {sorted(os.listdir(dest))}", flush=True)


def ensure_vad():
    dest = os.path.join(MODELS, "silero_vad.onnx")
    if os.path.exists(dest):
        return
    _download(VAD_URL, dest)


def ensure_tts():
    dest = os.path.join(MODELS, "tts", TTS_NAME)
    if os.path.exists(os.path.join(dest, "model.onnx")):
        return
    archive = os.path.join(CACHE, TTS_NAME + ".tar.bz2")
    _download(TTS_URL, archive)
    tts_root = os.path.join(MODELS, "tts")
    os.makedirs(tts_root, exist_ok=True)
    _extract_tarbz2(archive, tts_root)
    if not os.path.exists(os.path.join(dest, "model.onnx")):
        raise SystemExit(f"[fetch] TTS 解压后未找到 {dest}")
    print(f"[fetch] TTS -> {dest}", flush=True)


def ensure_argos():
    from translate_engine import ensure_pair  # 需已 pip install requirements.txt
    for s, d in ARGOS_PAIRS:
        ok = ensure_pair(s, d)
        print(f"[fetch] argos {s}->{d}: {ok}", flush=True)


def main():
    ensure_asr()
    ensure_vad()
    ensure_tts()
    ensure_argos()
    print("[fetch] ALL DONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())

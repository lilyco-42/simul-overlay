# -*- coding: utf-8 -*-
"""下载中英双语流式 ASR 模型到 app/src/main/assets（gitignore，本地/CI 构建前跑一次）。

模型: sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20（中英双语，endpoint 断句）
来源: GitHub Releases (k2-fsa/sherpa-onnx)，约 75MB。
幂等：tokens.txt 已存在即退出。
"""
import os
import shutil
import sys
import tarfile
import urllib.request

NAME = "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"
URL = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{NAME}.tar.bz2"
ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "app", "src", "main", "assets")
DEST = os.path.join(ASSETS, NAME)
MARKER = os.path.join(DEST, "tokens.txt")
CACHE_DIR = os.path.join(ROOT, ".cache")
ARCHIVE = os.path.join(CACHE_DIR, NAME + ".tar.bz2")


# 运行时只用这 4 个文件（MainActivity 配置：int8 encoder + fp32 decoder + int8 joiner），
# 其余（fp32 encoder 315MB、int8 decoder、fp32 joiner、test_wavs、bpe）一律剪掉，APK 从 531MB → 190MB。
KEEP = {
    "encoder-epoch-99-avg-1.int8.onnx",
    "decoder-epoch-99-avg-1.onnx",
    "joiner-epoch-99-avg-1.int8.onnx",
    "tokens.txt",
}


def prune(dest):
    """幂等瘦身：删除 dest 下不在 KEEP 的条目。"""
    removed = 0
    for name in os.listdir(dest):
        if name in KEEP:
            continue
        p = os.path.join(dest, name)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            os.remove(p)
        removed += 1
    if removed:
        print(f"[model] pruned {removed} extra entries -> {sorted(os.listdir(dest))}", flush=True)


def main():
    if os.path.exists(MARKER):
        prune(DEST)  # 已有模型也先剪冗余（幂等）
        print(f"[model] already present: {DEST}")
        return
    os.makedirs(CACHE_DIR, exist_ok=True)

    if not os.path.exists(ARCHIVE) or os.path.getsize(ARCHIVE) == 0:
        print(f"[model] downloading {URL} ...", flush=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        part = ARCHIVE + ".part"
        with urllib.request.urlopen(req, timeout=600) as r, open(part, "wb") as f:
            total = 0
            last = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
                if total - last >= 20 << 20:
                    print(f"[model]   {total // (1 << 20)} MB", flush=True)
                    last = total
        os.replace(part, ARCHIVE)
        print(f"[model] downloaded {os.path.getsize(ARCHIVE) // (1 << 20)} MB", flush=True)

    print("[model] extracting ...", flush=True)
    with tarfile.open(ARCHIVE, "r:bz2") as tar:
        try:
            tar.extractall(CACHE_DIR, filter="data")
        except TypeError:  # Python < 3.12 无 filter 参数
            tar.extractall(CACHE_DIR)

    extracted = os.path.join(CACHE_DIR, NAME)
    os.makedirs(ASSETS, exist_ok=True)
    if os.path.exists(DEST):
        shutil.rmtree(DEST)
    shutil.move(extracted, DEST)
    prune(DEST)
    print(f"[model] done -> {DEST}", flush=True)


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""批量安装语对包（走 translate_engine._download_pkg 的抗 403 下载路径）。

用法: python install_pairs.py [语种代码...]
默认安装 11 语种 × 双向（en 枢纽）= 22 个语对包。
"""
import sys
import time

from translate_engine import ensure_pair

langs = sys.argv[1:] or ["ja", "ko", "de", "fr", "es", "ru", "vi", "th", "ar", "it", "pt"]
tasks = [(s, d) for L in langs for s, d in [("en", L), (L, "en")]]
total = len(tasks)

for i, (s, d) in enumerate(tasks, 1):
    t = time.time()
    try:
        ok = ensure_pair(s, d)
        print(f"[{i}/{total}] {s}->{d}: {ok} ({time.time() - t:.1f}s)", flush=True)
    except Exception as e:
        print(f"[{i}/{total}] {s}->{d}: FAIL {e}", flush=True)

print("ALL DONE", flush=True)

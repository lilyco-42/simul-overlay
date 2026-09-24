# -*- coding: utf-8 -*-
"""最小化验证 2/2：麦克风实时 → 流式ASR → 离线NMT → 控制台实时双语字幕

用法: python demo_mic.py   （对着麦克风说话，Ctrl+C 退出）
"""
import queue
import sys
import time
import numpy as np
import sounddevice as sd

from pipeline import build_recognizer, emit, Segmenter

SR = 16000
CHUNK = int(0.1 * SR)  # sounddevice block size
MAX_SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 45.0  # 默认45秒自动退出

recognizer = build_recognizer()
seg = Segmenter(recognizer, on_emit=emit)
q: queue.Queue[np.ndarray] = queue.Queue()

def callback(indata, frames, time_info, status):
    if status:
        print(f"[audio] {status}", file=sys.stderr, flush=True)
    q.put(indata.copy())

print(f"[mic] listening for {MAX_SECONDS:.0f}s... speak now (Ctrl+C to stop early)\n", flush=True)
start = time.time()
last_level_print = 0.0

try:
    with sd.InputStream(samplerate=SR, channels=1, dtype="float32",
                        blocksize=CHUNK, callback=callback):
        while time.time() - start < MAX_SECONDS:
            samples = q.get()
            rms = float(np.sqrt(np.mean(samples ** 2)))
            now = time.time()
            if now - last_level_print >= 1.0:
                bar = "#" * min(int(rms * 5000), 40)
                print(f"[level {now-start:4.1f}s] {rms:.4f} {bar}", flush=True)
                last_level_print = now
            seg.push(samples.reshape(-1))
except KeyboardInterrupt:
    pass

seg.finish()
print(f"\n[mic] stopped after {time.time()-start:.0f}s.")

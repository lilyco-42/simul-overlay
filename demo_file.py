# -*- coding: utf-8 -*-
"""最小化验证 1/2：wav → VAD门控 → 流式ASR → 离线NMT → 双语字幕

用法: python demo_file.py <wav路径> [--no-vad]
  --no-vad 关闭 VAD（对照组，复现旧版行为）
"""
import sys
import time
import numpy as np
import soundfile as sf

from pipeline import build_recognizer, emit, feed, Segmenter

args = [a for a in sys.argv[1:] if not a.startswith("--")]
USE_VAD = "--no-vad" not in sys.argv
WAV = args[0] if args else \
    "D:/Code/simul-demo/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20/test_wavs/0.wav"

recognizer = build_recognizer()
audio, sr = sf.read(WAV, dtype="float32")
if sr != 16000:
    sys.exit(f"expect 16kHz wav, got {sr} (先用 ffmpeg -ar 16000 -ac 1 重采样)")

print(f"[file] {len(audio)/sr:.1f}s audio, VAD={'ON' if USE_VAD else 'OFF'}\n")
t0 = time.time()

if USE_VAD:
    seg = Segmenter(recognizer, on_emit=emit)
    CHUNK = int(sr * 1.0)  # 每秒推进一次，VAD 在内部按 32ms 窗消费
    for i in range(0, len(audio), CHUNK):
        seg.push(audio[i:i + CHUNK])
    seg.finish()
else:
    stream = recognizer.create_stream()
    CHUNK = int(0.1 * sr)
    for i in range(0, len(audio), CHUNK):
        feed(recognizer, stream, audio[i:i + CHUNK])
        if recognizer.is_endpoint(stream):
            emit(recognizer.get_result(stream))
            recognizer.reset(stream)
        time.sleep(CHUNK / sr / 4)
    rest = recognizer.get_result(stream).strip()
    if rest:
        emit(rest)

print(f"\n[file] done in {time.time()-t0:.1f}s ({len(audio)/sr/(time.time()-t0):.1f}x realtime)")

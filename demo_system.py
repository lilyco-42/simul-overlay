# -*- coding: utf-8 -*-
"""M1：WASAPI loopback 系统声音实时翻译（游戏/视频无需麦克风，直接抓系统音频）

用法: python demo_system.py [秒数，默认60]
  （播放任意系统声音/视频/游戏，字幕实时输出；Ctrl+C 提前退出）

原理: Windows WASAPI loopback 把"扬声器正在播放的声音"当作输入设备捕获
      → int16 多声道 → 混单 → 重采样 16k → 复用与 demo_mic 相同的
      VAD 门控 + 流式 ASR + 离线NMT 管线。
"""
import sys
import time

import numpy as np
import pyaudiowpatch as pyaw

from pipeline import build_recognizer, emit, Segmenter

SR = 16000
MAX_SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0


def resample(x, sr_in):
    if sr_in == SR:
        return x
    n_out = int(len(x) * SR / sr_in)
    if n_out <= 0:
        return x[:0]
    t_in = np.arange(len(x)) / sr_in
    t_out = np.arange(n_out) / SR
    return np.interp(t_out, t_in, x).astype(np.float32)


def pick_loopback(p):
    """选中默认输出设备对应的 loopback（回环）输入设备。"""
    wasapi = p.get_host_api_info_by_type(pyaw.paWASAPI)
    default_out = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
    if not default_out.get("isLoopbackDevice"):
        for lb in p.get_loopback_device_info_generator():
            if default_out["name"] in lb["name"]:
                return lb, default_out
        # 兜底：拿第一个 loopback 设备
        for lb in p.get_loopback_device_info_generator():
            return lb, default_out
    return default_out, default_out


recognizer = build_recognizer()
seg = Segmenter(recognizer, on_emit=emit)

with pyaw.PyAudio() as p:  # pyaudiowpatch 的类名就是 PyAudio（WASAPI 补丁版）
    dev, out = pick_loopback(p)
    sr_in = int(dev["defaultSampleRate"])
    ch = int(dev["maxInputChannels"])
    print(f"[system-audio] output: {out['name']}", flush=True)
    print(f"[system-audio] loopback: {dev['name']}  rate={sr_in} ch={ch}", flush=True)
    print(f"[system-audio] listening {MAX_SECONDS:.0f}s — 播放任意系统声音即可，Ctrl+C 提前退出\n",
          flush=True)

    block = int(sr_in * 0.1)  # 100ms
    start = time.time()
    last_level = 0.0
    try:
        with p.open(format=pyaw.paInt16, channels=ch, rate=sr_in,
                    input=True, input_device_index=dev["index"],
                    frames_per_buffer=block) as stream:
            while time.time() - start < MAX_SECONDS:
                raw = stream.read(block, exception_on_overflow=False)
                x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                if ch > 1:
                    x = x.reshape(-1, ch).mean(axis=1)
                rms = float(np.sqrt(np.mean(x ** 2)))
                now = time.time()
                if now - last_level >= 1.0:
                    bar = "#" * min(int(rms * 5000), 40)
                    print(f"[level {now-start:4.1f}s] {rms:.4f} {bar}", flush=True)
                    last_level = now
                seg.push(resample(x, sr_in))
    except KeyboardInterrupt:
        pass

seg.finish()
print(f"\n[system-audio] stopped after {time.time()-start:.0f}s.")

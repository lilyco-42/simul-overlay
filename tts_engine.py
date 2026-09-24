# -*- coding: utf-8 -*-
"""M2：TTS 朗读（反向语音输出）—— sherpa-onnx OfflineTts + Kokoro multi-lang v1.0。

模型: models/tts/kokoro-multi-lang-v1_0（310MB，en/zh/ja/es/fr/it/pt 七语种，24kHz）
用法:
  python tts_engine.py "要朗读的文本" [语种] [--play]   # 生成 wav，--play 直接播放
  代码内: from tts_engine import speak; speak(text, lang="en")
"""
import sys
import threading
import wave
from pathlib import Path

import numpy as np

import sherpa_onnx

MODEL_DIR = Path(__file__).parent / "models" / "tts" / "kokoro-multi-lang-v1_0"

# 语种 → 默认音色 sid（kokoro-multi-lang-v1_0，53 speakers；详见 k2-fsa 文档）
SID = {
    "en": 3,   # af_heart（美音女声）
    "zh": 47,  # zf_xiaoxiao
    "ja": 37,  # jf_alpha
    "es": 28,  # ef_dora
    "fr": 30,  # ff_siwis
    "it": 35,  # if_sara
    "pt": 42,  # pf_dora
    # v1.0 无 ko/de/ru/vi/th/ar 音色 → 英文音色兜底（后续可升级 v1.1 103 音色）
    "ko": 3, "de": 3, "ru": 3, "vi": 3, "th": 3, "ar": 3,
}

_tts = None
_lock = threading.Lock()


def _get_tts():
    global _tts
    with _lock:
        if _tts is None:
            if not (MODEL_DIR / "model.onnx").exists():
                raise FileNotFoundError(f"TTS 模型缺失: {MODEL_DIR}")
            lexicon = ",".join(
                str(p) for p in [MODEL_DIR / "lexicon-us-en.txt", MODEL_DIR / "lexicon-zh.txt"]
                if p.exists())
            rule_fsts = ",".join(
                str(p) for p in [MODEL_DIR / "date-zh.fst", MODEL_DIR / "number-zh.fst",
                                 MODEL_DIR / "phone-zh.fst"] if p.exists())
            model_cfg = sherpa_onnx.OfflineTtsModelConfig(
                kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                    model=str(MODEL_DIR / "model.onnx"),
                    voices=str(MODEL_DIR / "voices.bin"),
                    tokens=str(MODEL_DIR / "tokens.txt"),
                    data_dir=str(MODEL_DIR / "espeak-ng-data"),
                    lexicon=lexicon),
                num_threads=2,
                provider="cpu")
            cfg = sherpa_onnx.OfflineTtsConfig(model=model_cfg, rule_fsts=rule_fsts)
            _tts = sherpa_onnx.OfflineTts(cfg)
    return _tts


def synthesize(text, lang="en", out_wav=None, sid=None, speed=1.0):
    """合成语音，返回 (samples float32 -1..1, sample_rate)；out_wav 非空时同时落盘。"""
    tts = _get_tts()
    if sid is None:
        sid = SID.get(lang, 3)
    audio = tts.generate(text, sid=sid, speed=speed)
    samples = np.asarray(audio.samples, dtype=np.float32)
    sr = audio.sample_rate
    if out_wav:
        pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
        with wave.open(str(out_wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(pcm.tobytes())
    return samples, sr


def speak(text, lang="en", **kw):
    """合成并立即播放（依赖 sounddevice）。"""
    import sounddevice as sd
    samples, sr = synthesize(text, lang, **kw)
    sd.play(samples, sr)
    sd.wait()
    return samples, sr


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)
    text = args[0]
    lang = args[1] if len(args) > 1 else None
    lang = lang or ("zh" if any("一" <= c <= "鿿" for c in text) else "en")
    out = Path(__file__).parent / f"tts_out_{lang}.wav"
    samples, sr = synthesize(text, lang, out_wav=out)
    print(f"[tts] lang={lang} sid={SID.get(lang, 3)} dur={len(samples)/sr:.1f}s -> {out}")
    if "--play" in sys.argv:
        speak(text, lang)  # 复用缓存的 _tts，重新合成播放（原型够用）

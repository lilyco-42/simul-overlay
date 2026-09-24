# -*- coding: utf-8 -*-
"""同传管线核心模块（原子单元）：音频流 → sherpa-onnx 流式ASR → Argos离线NMT → 双语字幕行"""
import re
import numpy as np
import sherpa_onnx
from argostranslate import translate as argos

MODEL_DIR = "D:/Code/simul-demo/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"


def build_recognizer():
    return sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=f"{MODEL_DIR}/tokens.txt",
        encoder=f"{MODEL_DIR}/encoder-epoch-99-avg-1.int8.onnx",
        decoder=f"{MODEL_DIR}/decoder-epoch-99-avg-1.int8.onnx",
        joiner=f"{MODEL_DIR}/joiner-epoch-99-avg-1.int8.onnx",
        num_threads=2,
        provider="cpu",
        enable_endpoint_detection=True,
        rule1_min_trailing_silence=1.0,
        rule2_min_trailing_silence=0.6,
        debug=False,
    )


def feed(recognizer, stream, samples):
    """喂一段音频并解码到尽头"""
    stream.accept_waveform(16000.0, samples)
    while recognizer.is_ready(stream):
        recognizer.decode_stream(stream)


VAD_PATH = "D:/Code/simul-demo/models/silero_vad.onnx"


def build_vad(threshold=0.5):
    cfg = sherpa_onnx.VadModelConfig(
        sample_rate=16000,
        silero_vad=sherpa_onnx.SileroVadModelConfig(
            model=VAD_PATH,
            threshold=threshold,
            min_speech_duration=0.25,
            min_silence_duration=0.5,
            max_speech_duration=20.0,
            window_size=512,
        ),
        num_threads=2,
        provider="cpu",
        debug=False,
    )
    return sherpa_onnx.VadModel.create(cfg)


class Segmenter:
    """VAD 门控分段器：只有语音窗才进 ASR，静音/BGM ≥0.6s 即切段出字幕。

    解决实测发现的两个问题：
      1) BGM/片头音乐喂给 ASR 产生 "SIL..." 幻觉与叠字
      2) 无标点长段粘连 → 按自然停顿切句，NMT 翻译质量随之提升
    """

    ENTER_STREAK = 2        # 连续 2 个语音窗(≈64ms) 进入说话态
    EXIT_WINDOWS = 12       # 连续 12 个静音窗(≈0.6s) 切段
    MAX_SPEECH_WINDOWS = 400  # 兜底：单段最长 ≈12.8s 强制切段

    def __init__(self, recognizer, on_emit, threshold=0.5):
        self.recognizer = recognizer
        self.vad = build_vad(threshold)
        self.on_emit = on_emit
        ws = self.vad.window_size
        self.win = ws() if callable(ws) else ws
        self.stream = recognizer.create_stream()
        self.buf = np.zeros(0, dtype=np.float32)
        self.speaking = False
        self.sp_streak = 0
        self.ns_streak = 0
        self.speech_len = 0

    def push(self, samples):
        self.buf = np.concatenate([self.buf, np.asarray(samples, dtype=np.float32)])
        while len(self.buf) >= self.win:
            w = self.buf[:self.win]
            self.buf = self.buf[self.win:]
            self._step(w)

    def _step(self, w):
        if not self.speaking:
            self.sp_streak = self.sp_streak + 1 if self.vad.is_speech(w) else 0
            if self.sp_streak >= self.ENTER_STREAK:
                self.speaking = True
                self.ns_streak = 0
                self.speech_len = 0
                feed(self.recognizer, self.stream, w)  # 进入时补喂当前窗
        else:
            if self.vad.is_speech(w):
                self.ns_streak = 0
                self.speech_len += 1
                feed(self.recognizer, self.stream, w)
                if self.speech_len >= self.MAX_SPEECH_WINDOWS:
                    self.flush()
            else:
                self.ns_streak += 1
                if self.ns_streak >= self.EXIT_WINDOWS:
                    self.flush()

    def flush(self):
        if self.speaking:
            text = self.recognizer.get_result(self.stream)
            self.recognizer.reset(self.stream)
            self.on_emit(text)
        self.speaking = False
        self.sp_streak = 0
        self.ns_streak = 0
        self.speech_len = 0

    def finish(self):
        self.flush()
        if len(self.buf):
            self.buf = np.zeros(0, dtype=np.float32)


def cleanup_text(text: str) -> str:
    """轻量清洗 ASR 叠字与回声（实测产物）：
    - 折叠 3 连以上相同汉字（内内内→内），保留 2 连合法词（谢谢/常常）
    - 折叠 4 连以上相同英文 token 片段（you-you-you-you → you）
    """
    text = re.sub(r"([\u4e00-\u9fff])\1{2,}", r"\1", text)
    text = re.sub(r"\b(\w+)(?:-\1){3,}\b", r"\1", text)
    return text


def detect_lang(text: str) -> str:
    return "zh" if re.search(r"[一-鿿]", text) else "en"


def translate_line(text: str) -> str:
    """离线双向翻译：中文→英文 / 英文→中文"""
    text = cleanup_text(text)
    src = detect_lang(text)
    dst = "en" if src == "zh" else "zh"
    try:
        return argos.translate(text, src, dst)
    except Exception as e:  # 翻译失败不阻塞字幕
        return f"[NMT error: {e}]"


def emit(source: str):
    """产出一行双语字幕"""
    source = cleanup_text(source).strip()
    if not source:
        return
    target = translate_line(source)
    print(f"  {source}", flush=True)
    print(f"→ {target}", flush=True)
    print("-" * 48, flush=True)

# -*- coding: utf-8 -*-
"""M3：屏幕文字 OCR 翻译（游戏文本 / 小说 / 网页），离线 RapidOCR + 引擎层翻译。

用法:
  python demo_ocr.py                        # 全屏，每 2s 抓一次，新文本即翻译
  python demo_ocr.py 100,200,900,700 3      # 指定区域 x1,y1,x2,y2 + 间隔秒
  python demo_ocr.py --once                 # 只抓一次（配区域用）
  python demo_ocr.py --img screenshot.png   # 直接翻译图片文件（阅读模式底座）
Ctrl+C 退出；字幕历史照常导出 subtitle_session.txt/.srt。
"""
import sys
import time

import numpy as np

from pipeline import emit


def make_engine():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


def ocr_image(engine, img):
    """img: PIL.Image / ndarray / 路径 → 拼接文本（阅读顺序：按 y 再 x 排）。"""
    out = engine(img)
    result = out[0] if isinstance(out, tuple) else out
    if not result:
        return ""
    items = []
    for box, text, score in result:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        items.append((min(ys), min(xs), text))
    items.sort()
    return " ".join(t for _, _, t in items).strip()


def main():
    args = [a for a in sys.argv[1:]]
    once = "--once" in args
    args = [a for a in args if a != "--once"]
    img_path = None
    region = None
    interval = 2.0
    if args and args[0] == "--img":
        img_path = args[1]
        args = args[2:]
    if args and "," in args[0]:
        region = tuple(int(v) for v in args[0].split(","))
        args = args[1:]
    if args:
        interval = float(args[0])

    engine = make_engine()

    if img_path:
        text = ocr_image(engine, img_path)
        print(f"[ocr] {text}\n", flush=True)
        emit(text)
        return

    from PIL import ImageGrab
    print(f"[ocr] region={region or 'full-screen'} interval={interval}s "
          f"(Ctrl+C 退出)\n", flush=True)
    last = None
    try:
        while True:
            shot = ImageGrab.grab(bbox=region, all_screens=True)
            text = ocr_image(engine, np.array(shot))
            if text and text != last:
                emit(text)
                last = text
            if once:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

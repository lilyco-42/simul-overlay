# -*- coding: utf-8 -*-
"""M3：屏幕文字 OCR 翻译（游戏文本 / 小说 / 网页），离线 RapidOCR + 引擎层翻译。

用法:
  python demo_ocr.py --select                  # ★拖拽圈一块屏，实时OCR翻成中文（默认目标语种）
  python demo_ocr.py                        # 全屏，每 2s 抓一次，新文本即翻译
  python demo_ocr.py 100,200,900,700 3      # 指定区域 x1,y1,x2,y2 + 间隔秒
  python demo_ocr.py --once                 # 只抓一次（配区域用）
  python demo_ocr.py --img screenshot.png   # 直接翻译图片文件（阅读模式底座）
环境变量 SIMUL_TARGET_LANG=zh 可恒定翻译为中文（默认: 非中文→中文, 中文→英文）。
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


def select_region() -> tuple:
    """全屏半透明遮罩拖拽选区 → (x1,y1,x2,y2) 屏幕坐标（tkinter，零新依赖）。"""
    import tkinter as tk

    root = tk.Tk()
    root.attributes("-topmost", True)
    if sys.platform == "win32":
        import ctypes
        u32 = ctypes.windll.user32
        vx, vy = u32.GetSystemMetrics(76), u32.GetSystemMetrics(77)   # 虚拟屏原点（多显示器）
        vw, vh = u32.GetSystemMetrics(78), u32.GetSystemMetrics(79)
    else:
        vx, vy, vw, vh = 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{vw}x{vh}+{vx}+{vy}")
    root.attributes("-alpha", 0.3)
    canvas = tk.Canvas(root, cursor="cross", bg="black")
    canvas.pack(fill="both", expand=True)
    state = {"x0": 0, "y0": 0, "rect": None}

    def press(e):
        x, y = e.x_root, e.y_root
        state["x0"], state["y0"] = x, y
        state["rect"] = canvas.create_rectangle(x - vx, y - vy, x - vx, y - vy,
                                                outline="red", width=2)

    def drag(e):
        if state["rect"]:
            canvas.coords(state["rect"], state["x0"] - vx, state["y0"] - vy,
                          e.x_root - vx, e.y_root - vy)

    def release(e):
        x1, y1 = state["x0"], state["y0"]
        x2, y2 = e.x_root, e.y_root
        root.destroy()
        sel["box"] = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

    sel = {}
    canvas.bind("<ButtonPress-1>", press)
    canvas.bind("<B1-Motion>", drag)
    canvas.bind("<ButtonRelease-1>", release)
    root.mainloop()
    return sel.get("box")


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

    if "--select" in args:
        region = select_region()
        if not region:
            print("[ocr] 未选择区域", flush=True)
            return
        print(f"[ocr] 选区 {region}", flush=True)

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

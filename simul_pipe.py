# -*- coding: utf-8 -*-
"""PyInstaller 统一入口：simul-pipe <system|mic|ocr|read> [args...]

打包后的离线包用法（与开发模式等价）：
  simul-pipe system 60        # 系统声音同传
  simul-pipe mic 60           # 麦克风同传
  simul-pipe ocr --select     # 拖拽圈选 OCR 翻译（参数与 demo_ocr.py 完全一致）
  simul-pipe read a.txt zh    # 整篇阅读双语（参数与 read_doc.py 完全一致）

实现：把子命令映射到原脚本，用 runpy 以 __main__ 语义执行——
demo_system/demo_mic 是顶层直跑脚本，read_doc 带 __main__ guard，两种结构都兼容。
"""
import os
import runpy
import sys

# —— PyInstaller 静态分析锚点 ——
# 四个子命令脚本经 runpy 动态执行，分析器从本文件出发看不到它们的 import 链；
# 显式 import 项目内纯模块确保收进 PYZ（frozen 下外挂脚本 from ... import 才能找到）。
# 只锚模块型文件：demo_* 是顶层直跑脚本，import 即执行，绝不能在此 import。
if getattr(sys, "frozen", False):
    import pipeline  # noqa: F401
    import translate_engine  # noqa: F401
    import tts_engine  # noqa: F401

CMD = {
    "system": "demo_system.py",
    "mic": "demo_mic.py",
    "ocr": "demo_ocr.py",
    "read": "read_doc.py",
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in CMD:
        print(__doc__)
        sys.exit(2)
    script = CMD[sys.argv[1]]
    # frozen(--onedir) 下数据脚本在 _MEIPASS；开发模式在本文件同目录
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, script)
    if not os.path.exists(path):
        path = script  # 开发模式：仓库根
    sys.argv = [script] + sys.argv[2:]
    runpy.run_path(path, run_name="__main__")


if __name__ == "__main__":
    main()

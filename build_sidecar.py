# -*- coding: utf-8 -*-
"""跨平台 PyInstaller 打包 simul-pipe 侧车（--add-data 分隔符按平台自动处理）。

用法: python build_sidecar.py
产出: dist/simul-pipe/（Windows: simul-pipe.exe；mac/linux: simul-pipe）
对应 GOAL M4：CI 三平台构建前调用，产物拷入 app/src-tauri/resources/simul-pipe。
"""
import os
import subprocess
import sys

SEP = ";" if os.name == "nt" else ":"
SCRIPTS = ["demo_system.py", "demo_mic.py", "demo_ocr.py", "read_doc.py"]
COLLECT = [
    "sherpa_onnx",
    "onnxruntime",
    "argostranslate",
    "ctranslate2",
    "sentencepiece",
    "rapidocr_onnxruntime",
    "pyaudiowpatch",
]


def main():
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onedir", "--name", "simul-pipe",
    ]
    for s in SCRIPTS:
        args += ["--add-data", f"{s}{SEP}."]
    for c in COLLECT:
        args += ["--collect-all", c]
    args += ["--hidden-import", "tkinter", "simul_pipe.py"]
    subprocess.run(args, check=True, cwd=os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    main()

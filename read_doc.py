# -*- coding: utf-8 -*-
"""阅读模式：整篇文本/小说 → 双语对照文档（原文 + 译文逐段排版）。

用法: python read_doc.py <输入.txt|md> [目标语种 zh/en]
输出: <输入>.bilingual.txt（同时打印进度）
段落切分：空行优先；无空行的长段按中文句读/英文句号分组打包（每包 ≈180 字符）。
"""
import re
import sys
from pathlib import Path

from translate_engine import translate, detect_lang


def split_paragraphs(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out = []
    for p in paras:
        if len(p) <= 220:
            out.append(p)
            continue
        # 长段（小说常见整章无空行）→ 按句打包
        sents = re.split(r"(?<=[。！？.!?;；])\s*", p)
        buf = ""
        for s in sents:
            if not s:
                continue
            if len(buf) + len(s) > 180 and buf:
                out.append(buf)
                buf = s
            else:
                buf += s
        if buf:
            out.append(buf)
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src_path = Path(sys.argv[1])
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    text = src_path.read_text(encoding="utf-8")
    paras = split_paragraphs(text)
    src_lang = detect_lang(text[:500]) or "zh"
    if dst is None:
        dst = "en" if src_lang in ("zh", "ja", "ko") else "zh"

    out_path = src_path.with_suffix(src_path.suffix + ".bilingual.txt")
    n = len(paras)
    print(f"[read] {src_path.name}: {n} 段, {src_lang} → {dst}", flush=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for i, p in enumerate(paras, 1):
            try:
                t = translate(p, src_lang, dst) or ""
            except Exception as e:
                t = f"[翻译失败: {e}]"
            f.write(f"{p}\n{t}\n\n")
            if i % 10 == 0 or i == n:
                print(f"[read] {i}/{n}", flush=True)
    print(f"[read] 完成 → {out_path}", flush=True)


if __name__ == "__main__":
    main()

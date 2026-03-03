#!/usr/bin/env python3
"""检查文档重复内容 - V5.8.1"""
from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent
readme = (root / "README.md").read_text(encoding="utf-8")
skill = (root / "SKILL.md").read_text(encoding="utf-8")

def normalize(s: str) -> list[str]:
    # 只提取非空文本行，去掉 markdown 标题符号，统一小写
    lines = []
    for line in s.splitlines():
        t = line.strip()
        if not t:
            continue
        t = re.sub(r"^#+\s*", "", t)
        lines.append(t.lower())
    return lines

r = set(normalize(readme))
s = set(normalize(skill))
common = r & s

# 忽略常见短句
common = {x for x in common if len(x) >= 20}

print(f"README 行集合: {len(r)}")
print(f"SKILL 行集合:  {len(s)}")
print(f"重合行数量:    {len(common)}")

# 简单阈值：超过 80 视为重复过多
if len(common) > 80:
    print("\n⚠️ 文档重复偏多，建议继续精简 SKILL.md 或去重 README.md")
    print("示例重合行（前20条）：")
    for i, line in enumerate(sorted(common)[:20], 1):
        print(f"{i:02d}. {line[:120]}")
    raise SystemExit(1)

print("\n✅ 文档重复在可接受范围内")
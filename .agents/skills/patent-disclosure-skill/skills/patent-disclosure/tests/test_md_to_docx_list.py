# -*- coding: utf-8 -*-
"""有序列表被标题隔开后，Word 须从 1 重计，不得跨章串号。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

from md_to_docx import convert_md_to_docx, _paragraph_num_id


SAMPLE = """### 1.2 现有技术存在的缺点

1. 缺点甲
2. 缺点乙

---

## 二、针对上述缺点，说明本发明所要解决的技术问题

1. 问题甲
2. 问题乙
"""


class MdToDocxListNumberingTests(unittest.TestCase):
    def test_ordered_lists_restart_after_heading(self) -> None:
        doc = convert_md_to_docx(SAMPLE, base_dir=None, prefer_omml=False)
        numbered = [p for p in doc.paragraphs if _paragraph_num_id(p) is not None]
        self.assertEqual(len(numbered), 4)
        ids = [_paragraph_num_id(p) for p in numbered]
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(ids[2], ids[3])
        self.assertNotEqual(ids[0], ids[2])
        self.assertEqual(numbered[2].text, "问题甲")
        self.assertEqual(numbered[3].text, "问题乙")

    def test_blank_line_inside_list_keeps_same_instance(self) -> None:
        md = "1. 甲\n\n2. 乙\n"
        doc = convert_md_to_docx(md, base_dir=None, prefer_omml=False)
        numbered = [p for p in doc.paragraphs if _paragraph_num_id(p) is not None]
        self.assertEqual(len(numbered), 2)
        self.assertEqual(_paragraph_num_id(numbered[0]), _paragraph_num_id(numbered[1]))


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG / "tools") not in sys.path:
    sys.path.insert(0, str(PKG / "tools"))

from book_to_skill_setup import find_book_to_skill
from playbook import ingest_distilled_skill, peek_source, reject_if_url, safe_slug
from vault_layout import list_history_case_paths, list_playbook_index_paths, write_oa_index


class PlaybookPeekTests(unittest.TestCase):
    def test_rejects_url(self):
        with self.assertRaises(ValueError):
            reject_if_url("https://example.com/book.pdf")

    def test_peek_likely_oa_related(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "book.txt"
            path.write_text(
                "审查意见通知书的意见陈述应针对创造性评述，引用专利法第22条第3款，"
                "并结合对比文件说明权利要求的区别技术特征。答复策略包括修改权利要求或仅陈述。"
                "常见反模式是承认对比文件公开了全部特征、或补入超范围的实验数据。"
                "审查指南中关于创造性的三步法应作为陈述结构，而不是空泛否认。",
                encoding="utf-8",
            )
            result = peek_source(path, max_pages=8)
            self.assertEqual(result["hint"], "likely")
            self.assertIn("创造性", result["keyword_hits"])

    def test_peek_unlikely(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "cook.txt"
            path.write_text(
                "红烧肉的做法是先焯水再煸炒糖色，加酱油炖四十分钟。"
                "配菜可选土豆和鸡蛋，火候以筷子能轻松插入为准。"
                "本章还介绍清蒸鱼、番茄炒蛋和家常豆腐的备料顺序，与专利审查无关。",
                encoding="utf-8",
            )
            result = peek_source(path)
            self.assertEqual(result["hint"], "unlikely")


class PlaybookIngestTests(unittest.TestCase):
    def test_ingest_copies_and_stays_out_of_case_search(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill = root / "distilled"
            skill.mkdir()
            (skill / "cheatsheet.md").write_text("# 创造性答复决策表\n", encoding="utf-8")
            (skill / "SKILL.md").write_text("# book skill\n", encoding="utf-8")
            src = root / "oa-book.txt"
            src.write_text("local", encoding="utf-8")
            oa = root / "oa"
            (oa / "cases" / "history").mkdir(parents=True)
            (oa / "cases" / "history" / "c1.md").write_text(
                "---\ncase_id: c1\ntitle: 案\n---\n\nbody\n",
                encoding="utf-8",
            )
            result = ingest_distilled_skill(
                skill_dir=skill,
                oa_root=oa,
                source_path=src,
                slug="oa-tactics",
                title="答复实务",
            )
            self.assertTrue(result["ok"])
            dest = Path(result["dest"])
            self.assertTrue((dest / "cheatsheet.md").is_file())
            self.assertTrue((dest / "_playbook.md").is_file())
            write_oa_index(oa)
            index = (oa / "_OA索引.md").read_text(encoding="utf-8")
            self.assertIn("经验手册", index)
            self.assertIn("oa-tactics", index)
            history = list_history_case_paths(oa)
            self.assertTrue(any(p.name == "c1.md" for p in history))
            self.assertFalse(any("playbooks" in p.parts for p in history))
            self.assertEqual(len(list_playbook_index_paths(oa)), 1)

    def test_safe_slug(self):
        self.assertEqual(safe_slug("答复 实务!"), "答复-实务")


class BookToSkillDetectTests(unittest.TestCase):
    def test_find_from_env_dir(self):
        with tempfile.TemporaryDirectory() as td:
            skill = Path(td) / "book-to-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text("# book-to-skill\n", encoding="utf-8")
            import book_to_skill_setup as setup

            old = setup.os.environ.get("PATENT_OA_SKILLS_DIR")
            setup.os.environ["PATENT_OA_SKILLS_DIR"] = td
            try:
                found = find_book_to_skill()
                self.assertEqual(found, skill)
            finally:
                if old is None:
                    setup.os.environ.pop("PATENT_OA_SKILLS_DIR", None)
                else:
                    setup.os.environ["PATENT_OA_SKILLS_DIR"] = old


if __name__ == "__main__":
    unittest.main()

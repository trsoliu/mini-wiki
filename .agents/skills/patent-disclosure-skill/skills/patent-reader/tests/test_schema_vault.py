# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(PKG / "tools"))

from vault.schema_vault import (
    appearance_canvas_cards,
    load_structure_schema,
    render_structure_section_md,
    resolve_schema_files,
    structure_canvas_cards,
    upsert_structure_section,
)


class SchemaVaultTests(unittest.TestCase):
    def test_render_and_upsert(self) -> None:
        schema = {
            "parts": [
                {"id": "1", "name": "基板", "shape": "板状"},
                {"id": "2", "name": "卡扣臂", "shape": "臂状"},
            ],
            "relations": [{"from": "1", "to": "2", "type": "卡扣", "where": "侧缘"}],
            "uncertain": ["尺寸未知"],
        }
        sec = render_structure_section_md(schema)
        self.assertIn("## 结构说明", sec)
        self.assertNotIn("StructureSchema", sec)
        self.assertNotIn("structure_schema.json", sec)
        self.assertIn("基板", sec)
        self.assertIn("1 基板", sec)
        self.assertIn("2 卡扣臂", sec)
        note = "# t\n\n## 五、专利内术语表\n\n| a | b |\n\n## 六、特征\n\nx\n"
        out = upsert_structure_section(note, sec)
        self.assertIn("## 结构说明", out)
        self.assertNotIn("（StructureSchema）", out)
        self.assertIn("## 六、特征", out)

    def test_upsert_replaces_legacy_heading(self) -> None:
        legacy = (
            "# t\n\n## 结构说明（StructureSchema）\n\n"
            "> 由 `structure_schema.json` 入库生成\n\n"
            "## 六、特征\n\nx\n"
        )
        sec = render_structure_section_md(
            {"parts": [{"id": "9", "name": "钩部"}], "relations": []}
        )
        out = upsert_structure_section(legacy, sec)
        self.assertIn("## 结构说明\n", out)
        self.assertNotIn("StructureSchema", out)
        self.assertIn("钩部", out)

    def test_resolve_workdir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wd = Path(td)
            (wd / "structure_schema.json").write_text(
                json.dumps({"parts": [{"id": "1", "name": "A"}], "relations": []}),
                encoding="utf-8",
            )
            s, a = resolve_schema_files(wd)
            self.assertEqual(load_structure_schema(s).get("parts")[0]["name"], "A")
            self.assertFalse(a)

    def test_canvas_cards(self) -> None:
        cards = structure_canvas_cards({"parts": [{"id": "1", "name": "x"}], "relations": []})
        self.assertEqual(len(cards), 1)
        self.assertIn("结构", cards[0]["text"])
        cards2 = appearance_canvas_cards(
            {"product_name": "灯", "overall_shape": "圆", "design_points": ["罩"]}
        )
        self.assertEqual(len(cards2), 1)


if __name__ == "__main__":
    unittest.main()

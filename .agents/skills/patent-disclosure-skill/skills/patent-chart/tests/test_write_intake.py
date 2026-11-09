# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from write_intake import (
    load_intake,
    main,
    make_session_dir,
    missing_fields,
    normalize_intake,
    write_intake,
)


class WriteIntakeTests(unittest.TestCase):
    def test_normalize_paths_and_url(self) -> None:
        pub = normalize_intake(
            {
                "scene": "invalidity",
                "left": {"pub_number": "CN1", "paths": ["a.pdf"]},
                "right": [{"kind": "patent", "pub_number": "CN2"}],
            },
            case_dir=Path("."),
        )
        self.assertEqual(pub["left"]["source"], "pub")
        self.assertEqual(pub["left"]["paths"], [])
        self.assertEqual(pub["right"][0]["pub_number"], "CN2")
        local = normalize_intake(
            {"scene": "patentability", "left": {"source": "local", "paths": ["a.pdf", "b.pdf"]}},
            case_dir=Path("."),
        )
        self.assertEqual(local["left"]["path"], "a.pdf")
        self.assertEqual(local["left"]["pub_number"], "")
        linked = normalize_intake(
            {
                "scene": "fto",
                "right": [{"pub_number": "某型号", "url": "www.example.com/p/1"}],
            },
            case_dir=Path("."),
        )
        self.assertEqual(linked["right"][0]["kind"], "product")
        self.assertEqual(linked["right"][0]["url"], "https://www.example.com/p/1")

    def test_missing_fields(self) -> None:
        empty = normalize_intake({}, case_dir=Path("sess"))
        self.assertIn("scene", missing_fields(empty))
        self.assertIn("left", missing_fields(empty))
        self.assertIn("right", missing_fields(empty))
        product = normalize_intake(
            {
                "scene": "infringement",
                "left": {"pub_number": "CN1"},
                "right": [{"pub_number": "型号A"}],
            },
            case_dir=Path("sess"),
        )
        self.assertIn("right[1].evidence", missing_fields(product))
        ok = normalize_intake(
            {
                "scene": "infringement",
                "left": {"pub_number": "CN1"},
                "right": [{"pub_number": "型号A", "url": "https://example.com/p"}],
            },
            case_dir=Path("sess"),
        )
        self.assertEqual(missing_fields(ok), [])
        need_right = normalize_intake(
            {
                "scene": "patentability",
                "left": {"pub_number": "CN1"},
            },
            case_dir=Path("sess"),
        )
        self.assertIn("right", missing_fields(need_right))
        search_ok = normalize_intake(
            {
                "scene": "patentability",
                "left": {"pub_number": "CN1"},
                "search_fill": True,
            },
            case_dir=Path("sess"),
        )
        self.assertEqual(missing_fields(search_ok), [])
        fto_search = normalize_intake(
            {
                "scene": "fto",
                "left": {"pub_number": "CN1"},
                "search_fill": True,
            },
            case_dir=Path("sess"),
        )
        self.assertIn("right", missing_fields(fto_search))

    def test_write_and_check_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "raw.json"
            src.write_text(
                json.dumps(
                    {
                        "scene": "invalidity",
                        "case_id": "demo",
                        "left": {"pub_number": "CN1"},
                        "right": [{"pub_number": "CN2"}],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(main(["--dir", str(root), "--json", str(src)]), 0)
            sessions = [p for p in root.iterdir() if p.is_dir()]
            self.assertEqual(len(sessions), 1)
            saved = load_intake(sessions[0])
            self.assertEqual(saved["scene"], "invalidity")
            self.assertEqual(main(["--into", str(sessions[0]), "--check"]), 0)

    def test_refuse_incomplete_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "raw.json"
            src.write_text(json.dumps({"scene": "fto", "left": {"pub_number": "CN1"}}), encoding="utf-8")
            self.assertEqual(main(["--dir", str(root), "--json", str(src)]), 2)
            self.assertFalse([p for p in root.iterdir() if p.is_dir()])
            self.assertFalse(list(root.glob("**/intake.json")))

    def test_session_isolation_and_check_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = make_session_dir(root)
            second = make_session_dir(root)
            self.assertNotEqual(first, second)
            self.assertEqual(main(["--dir", str(root), "--alloc"]), 0)
            self.assertEqual(main(["--into", str(second), "--check"]), 1)
            data, missing = write_intake(
                {
                    "scene": "sep",
                    "left": {"pub_number": "CN1"},
                    "right": [{"pub_number": "GB/T 1", "text": "第5.2节"}],
                },
                session_dir=first,
            )
            self.assertEqual(missing, [])
            self.assertEqual(data["right"][0]["kind"], "standard")
            self.assertEqual(main(["--into", str(first), "--check"]), 0)
            self.assertEqual(main(["--into", str(second), "--check"]), 1)

    def test_alloc_then_write_keeps_start_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(main(["--dir", str(root), "--alloc"]), 0)
            session = next(p for p in root.iterdir() if p.is_dir())
            src = root / "raw.json"
            src.write_text(
                json.dumps(
                    {
                        "scene": "patentability",
                        "left": {"pub_number": "CN1"},
                        "right": [{"pub_number": "CN2"}],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(main(["--into", str(session), "--json", str(src)]), 0)
            self.assertEqual(load_intake(session)["session_id"], session.name)
            self.assertEqual([p.name for p in root.iterdir() if p.is_dir()], [session.name])


if __name__ == "__main__":
    unittest.main()

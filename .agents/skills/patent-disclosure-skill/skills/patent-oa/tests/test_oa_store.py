"""审查答复工具单测（不强制下载大 embedding 模型）。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
if str(PKG / "tools") not in sys.path:
    sys.path.insert(0, str(PKG / "tools"))

from case_md import chunk_case, dump_case_markdown, parse_case_markdown
from config import apply_preset, recommend_payload, write_config, load_config, PRESETS
from redact import redact_text
from store import init_db, search, search_by_tags, upsert_case, upsert_case_meta, _connect
from embed import Embedder, EmbedError


class RedactTests(unittest.TestCase):
    def test_company_and_phone(self):
        text, notes = redact_text("申请人上海某某科技有限公司电话13812345678")
        self.assertIn("申请人甲", text)
        self.assertIn("【电话已脱敏】", text)
        self.assertTrue(notes)


class CaseMdTests(unittest.TestCase):
    def test_roundtrip(self):
        meta = {
            "case_id": "c1",
            "title": "t",
            "statutes": ["专利法第22条第3款"],
            "defect_types": ["inventiveness"],
        }
        body = "## 通知书要点\nhello\n\n## 策略\nworld\n"
        md = dump_case_markdown(meta, body)
        m2, b2 = parse_case_markdown(md)
        self.assertEqual(m2["case_id"], "c1")
        self.assertIn("通知书要点", b2)
        chunks = chunk_case(m2, b2)
        kinds = [k for k, _ in chunks]
        self.assertIn("header", kinds)
        self.assertTrue(any(k == "notice" for k in kinds))


class StoreVecTests(unittest.TestCase):
    def test_upsert_and_search(self):
        try:
            import sqlite_vec
        except ImportError:
            self.skipTest("sqlite-vec not installed")

        import sqlite3
        import sqlite_vec as sv

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.enable_load_extension(True)
        sv.load(conn)
        init_db(conn, 4, with_vec=True)
        v1 = np.array([1, 0, 0, 0], dtype=np.float32)
        v2 = np.array([0, 1, 0, 0], dtype=np.float32)
        upsert_case(
            conn,
            case={
                "case_id": "a",
                "title": "A",
                "patent_type": "invention",
                "statutes": ["专利法第22条第3款"],
                "defect_types": ["inventiveness"],
                "domain": "机械",
                "notice_kind": "office_action",
                "outcome": "granted",
                "strategy": ["amend_claims"],
                "compare_refs": [],
                "tags": ["oa/inventiveness"],
                "updated_at": "t",
            },
            note_path="a.md",
            body_text="body a",
            chunks=[("header", "创造性 机械", v1)],
        )
        upsert_case(
            conn,
            case={
                "case_id": "b",
                "title": "B",
                "patent_type": "invention",
                "statutes": ["专利法第26条第3款"],
                "defect_types": ["disclosure"],
                "domain": "软件",
                "notice_kind": "office_action",
                "outcome": "pending",
                "strategy": ["argue_only"],
                "compare_refs": [],
                "tags": ["oa/disclosure"],
                "updated_at": "t",
            },
            note_path="b.md",
            body_text="body b",
            chunks=[("header", "公开不充分", v2)],
        )
        hits = search(
            conn,
            query_vec=v1,
            top_k=2,
            statutes=["专利法第22条第3款"],
            defect_types=["inventiveness"],
        )
        self.assertTrue(hits)
        self.assertEqual(hits[0]["case_id"], "a")


class TagOnlySearchTests(unittest.TestCase):
    def test_meta_only_without_vec(self):
        import sqlite3

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn, 0, with_vec=False)
        upsert_case_meta(
            conn,
            case={
                "case_id": "t1",
                "title": "T",
                "patent_type": "invention",
                "statutes": ["专利法第22条第3款"],
                "defect_types": ["inventiveness"],
                "domain": "机械",
                "notice_kind": "office_action",
                "outcome": "pending",
                "strategy": [],
                "compare_refs": [],
                "tags": ["oa/inventiveness"],
                "updated_at": "t",
            },
            note_path="t1.md",
            body_text="body",
        )
        hits = search_by_tags(
            conn,
            top_k=5,
            defect_types=["inventiveness"],
            statutes=["专利法第22条第3款"],
        )
        self.assertEqual(hits[0]["case_id"], "t1")
        hits2 = search(conn, query_vec=None, top_k=5, defect_types=["inventiveness"])
        self.assertEqual(hits2[0]["case_id"], "t1")


class ConfigTests(unittest.TestCase):
    def test_recommend_and_set(self):
        from config import documents_dir, oa_home, default_sqlite_path

        payload = recommend_payload()
        self.assertEqual(payload["recommended"]["model"], "embedding-3")
        self.assertEqual(payload["recommended"]["provider"], "openai_compatible")
        self.assertTrue(payload.get("vector_optional"))
        self.assertIn("minimax", payload["presets"])
        self.assertIn("local", payload["presets"])
        self.assertIn("minimax", payload["providers"])
        self.assertIn("paths", payload)
        self.assertTrue(documents_dir().is_dir() or documents_dir().parent.is_dir())
        self.assertEqual(oa_home().name, "oa")
        self.assertTrue(str(default_sqlite_path()).endswith("oa_vectors.sqlite"))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "embedding.config.yaml"
            from config import skip_vector, check_rebuild_needed, apply_preset

            skip_vector(path)
            cfg0 = load_config(path)
            self.assertFalse(cfg0.get("vector_enabled"))
            self.assertTrue(cfg0.get("user_confirmed"))
            self.assertFalse(check_rebuild_needed(cfg0)["needed"])

            write_config(
                provider="openai_compatible",
                model="embedding-3",
                dimensions=1024,
                path=path,
                base_url="https://open.bigmodel.cn/api/paas/v4",
                api_key_env="ZHIPUAI_API_KEY",
            )
            cfg = load_config(path)
            self.assertEqual(cfg["provider"], "openai_compatible")
            self.assertEqual(cfg["dimensions"], 1024)
            self.assertTrue(cfg.get("user_confirmed"))
            self.assertTrue(cfg.get("vector_enabled"))
            self.assertEqual(cfg.get("api_key_env"), "ZHIPUAI_API_KEY")
            self.assertTrue(check_rebuild_needed(cfg)["needed"])

            path2 = Path(td) / "minimax.yaml"
            apply_preset("minimax", path2)
            mcfg = load_config(path2)
            self.assertEqual(mcfg["provider"], "minimax")
            self.assertEqual(mcfg["model"], PRESETS["minimax"]["model"])
            self.assertEqual(mcfg["api_key_env"], "MINIMAX_API_KEY")
            self.assertEqual(mcfg["group_id_env"], "MINIMAX_GROUP_ID")

            path3 = Path(td) / "local.yaml"
            apply_preset("local", path3)
            lcfg = load_config(path3)
            self.assertEqual(lcfg["provider"], "local")
            self.assertEqual(lcfg["dimensions"], 512)


class EmbedderVendorTests(unittest.TestCase):
    def test_openai_compatible_sends_dimensions(self):
        captured: dict = {}

        def fake_urlopen(req, timeout=120):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode("utf-8"))

            class Resp:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    return json.dumps(
                        {
                            "data": [
                                {"index": 0, "embedding": [0.0, 1.0, 0.0, 0.0]},
                            ]
                        }
                    ).encode("utf-8")

            return Resp()

        import embed as embed_mod

        old = embed_mod.urllib.request.urlopen
        embed_mod.urllib.request.urlopen = fake_urlopen  # type: ignore[assignment]
        try:
            emb = Embedder(
                {
                    "provider": "openai_compatible",
                    "model": "embedding-3",
                    "dimensions": 4,
                    "base_url": "https://open.bigmodel.cn/api/paas/v4",
                    "api_key_env": "ZHIPUAI_API_KEY",
                }
            )
            os_environ = __import__("os").environ
            old_key = os_environ.get("ZHIPUAI_API_KEY")
            os_environ["ZHIPUAI_API_KEY"] = "test-key"
            try:
                vec = emb.embed_one("hello", purpose="query")
            finally:
                if old_key is None:
                    os_environ.pop("ZHIPUAI_API_KEY", None)
                else:
                    os_environ["ZHIPUAI_API_KEY"] = old_key
        finally:
            embed_mod.urllib.request.urlopen = old  # type: ignore[assignment]

        self.assertEqual(captured["body"]["model"], "embedding-3")
        self.assertEqual(captured["body"]["dimensions"], 4)
        self.assertEqual(vec.shape, (4,))

    def test_minimax_body_shape(self):
        captured: dict = {}

        def fake_urlopen(req, timeout=120):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode("utf-8"))
            n = len(captured["body"].get("texts") or [])

            class Resp:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    return json.dumps(
                        {
                            "vectors": [[1.0, 0.0, 0.0]] * max(n, 1),
                            "base_resp": {"status_code": 0},
                        }
                    ).encode("utf-8")

            return Resp()

        import embed as embed_mod

        old = embed_mod.urllib.request.urlopen
        embed_mod.urllib.request.urlopen = fake_urlopen  # type: ignore[assignment]
        try:
            emb = Embedder(
                {
                    "provider": "minimax",
                    "model": "embo-01",
                    "dimensions": 3,
                    "base_url": "https://api.minimaxi.com/v1/embeddings",
                    "api_key_env": "MINIMAX_API_KEY",
                    "group_id_env": "MINIMAX_GROUP_ID",
                    "group_id": "gid-1",
                }
            )
            os_environ = __import__("os").environ
            old_key = os_environ.get("MINIMAX_API_KEY")
            os_environ["MINIMAX_API_KEY"] = "test-key"
            try:
                vecs = emb.embed_texts(["a", "b"], purpose="document")
                _ = emb.embed_one("q", purpose="query")
            finally:
                if old_key is None:
                    os_environ.pop("MINIMAX_API_KEY", None)
                else:
                    os_environ["MINIMAX_API_KEY"] = old_key
        finally:
            embed_mod.urllib.request.urlopen = old  # type: ignore[assignment]

        self.assertIn("GroupId=gid-1", captured["url"])
        self.assertEqual(captured["body"]["texts"], ["q"])
        self.assertEqual(captured["body"]["type"], "query")
        self.assertEqual(vecs.shape[0], 2)


class PdfExtractTests(unittest.TestCase):
    def test_extract_simple_pdf(self):
        try:
            import fitz
        except ImportError:
            self.skipTest("pymupdf not installed")
        from pdf_text import extract_pdf_text, read_document

        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "oa.pdf"
            doc = __import__("fitz").open()
            page = doc.new_page()
            # 用 TextWriter 写入可抽取的 Helvetica 文本层
            tw = __import__("fitz").TextWriter(page.rect)
            font = __import__("fitz").Font("helv")
            tw.append((72, 72), "Office Action Art.22 inventiveness rejection", font=font)
            tw.write_text(page)
            doc.save(pdf)
            doc.close()
            result = extract_pdf_text(pdf)
            self.assertTrue(result["ok"])
            self.assertIn("inventiveness", result["text"])
            self.assertGreater(result["char_count_nospace"], 20)
            md = Path(td) / "a.md"
            md.write_text("hello md", encoding="utf-8")
            r2 = read_document(md)
            self.assertEqual(r2["text"], "hello md")


class SecretsAndSelftestTests(unittest.TestCase):
    def test_write_secrets_and_resolve(self):
        from config import write_secrets, load_secrets, resolve_api_key

        with tempfile.TemporaryDirectory() as td:
            sp = Path(td) / "embedding.secrets.yaml"
            write_secrets(api_key="sk-test-123", path=sp)
            sec = load_secrets(sp)
            self.assertEqual(sec.get("api_key"), "sk-test-123")
            cfg = {
                "provider": "openai_compatible",
                "api_key_env": "ZZZ_NO_SUCH_ENV_FOR_OA_TEST",
            }
            # resolve reads default_secrets_path; patch via writing then monkey env empty
            # unit: resolve with env set
            os_environ = __import__("os").environ
            os_environ["ZZZ_NO_SUCH_ENV_FOR_OA_TEST"] = "from-env"
            try:
                self.assertEqual(resolve_api_key(cfg), "from-env")
            finally:
                os_environ.pop("ZZZ_NO_SUCH_ENV_FOR_OA_TEST", None)

    def test_selftest_skipped_when_disabled(self):
        from config import skip_vector, run_selftest

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "embedding.config.yaml"
            skip_vector(path)
            result = run_selftest(path)
            self.assertTrue(result.get("ok"))
            self.assertTrue(result.get("skipped"))


class VaultLayoutTests(unittest.TestCase):
    def test_migrate_and_index(self):
        from vault_layout import (
            migrate_legacy_layout,
            refresh_oa_vault,
            list_history_case_paths,
        )

        with tempfile.TemporaryDirectory() as td:
            oa = Path(td) / "oa"
            cases = oa / "cases"
            cases.mkdir(parents=True)
            (cases / "old-case.md").write_text(
                "---\ncase_id: old-case\ntitle: t\ndefect_types: [clarity]\n"
                "statutes: [专利法第26条第4款]\noutcome: granted\n---\n\n# t\n",
                encoding="utf-8",
            )
            actions = migrate_legacy_layout(oa)
            self.assertTrue(any("history" in a for a in actions))
            hist = oa / "cases" / "history" / "old-case.md"
            self.assertTrue(hist.is_file())
            result = refresh_oa_vault(cfg={"obsidian_oa_dir": "oa"}, vault=Path(td))
            self.assertTrue(result["ok"])
            self.assertTrue(Path(result["index"]).is_file())
            self.assertTrue(Path(result["canvas"]).is_file())
            self.assertTrue(Path(result["base"]).is_file())
            self.assertEqual(Path(result["base"]).name, "_OA看板.base")
            self.assertEqual(len(list_history_case_paths(oa)), 1)

    def test_inventory_threshold(self):
        from vault_layout import oa_inventory

        with tempfile.TemporaryDirectory() as td:
            vault = Path(td)
            oa = vault / "oa"
            hist = oa / "cases" / "history"
            hist.mkdir(parents=True)
            (hist / "c1.md").write_text("# c1\n", encoding="utf-8")
            (hist / "c2.md").write_text("# c2\n", encoding="utf-8")
            pb = oa / "playbooks" / "book-a"
            pb.mkdir(parents=True)
            (pb / "_playbook.md").write_text("# pb\n", encoding="utf-8")
            inv = oa_inventory(cfg={"obsidian_oa_dir": "oa"}, vault=vault)
            self.assertTrue(inv["ok"])
            self.assertEqual(inv["counts"]["history"], 2)
            self.assertEqual(inv["counts"]["playbooks"], 1)
            self.assertTrue(inv["below"]["history"])
            self.assertTrue(inv["below"]["playbooks"])
            self.assertTrue(inv["nudge"])
            full = oa_inventory(
                cfg={"obsidian_oa_dir": "oa"},
                vault=vault,
                min_history=2,
                min_playbooks=1,
            )
            self.assertFalse(full["nudge"])
            missing = oa_inventory(
                cfg={"obsidian_oa_dir": "oa"},
                vault=vault / "no-such-vault",
            )
            self.assertEqual(missing["counts"]["history"], 0)
            self.assertTrue(missing["nudge"])


if __name__ == "__main__":
    unittest.main()

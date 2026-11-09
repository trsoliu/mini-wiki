# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

os.environ["PATENT_MAP_SKIP_EMBED"] = "1"
_TEST_MAP_HOME = Path(tempfile.mkdtemp(prefix="patent-map-home-"))
os.environ["PATENT_MAP_HOME"] = str(_TEST_MAP_HOME)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from serve_map import MapHandler  # noqa: E402
from ipc_titles import load_ipc_subclasses, resolve_ipc_csv  # noqa: E402
from ipc_scheme.parse import finalize_zh, parse_en_xml, parse_ipcpub_json  # noqa: E402
from ipc_scheme.download import ipcpub_scheme_json_url  # noqa: E402
from map_cache import cache_dir_for_vault, cache_db_path, documents_dir, map_home, skill_data_root  # noqa: E402
from vault_index import apply_domain_filter, build_payload, domain_id_of, scan_vault  # noqa: E402
from embed_layout import compose_embed_text, nearest_k, project_2d  # noqa: E402
from model_store import HUB_ENDPOINTS, default_model_dir, find_local_model, is_model_ready  # noqa: E402


def _note(pub: str) -> str:
    return f"""---
pub_number: {pub}
domain: 车辆工程
ipc: H02K9/19
ipc_codes:
  - H02K9/19
assignees:
  - 示例汽车股份有限公司
organizations:
  - 示例汽车股份有限公司
inventors:
  - 王一
filing_date: 2023-04-12
publication_date: 2025-02-01
cited_pubs:
  - CN114552122A
---

# 专利解读：热管理

## 一、一句话

油冷带走热量。

## 五、专利内术语表

| 术语 | 本文含义/位置 | 备注 |
| --- | --- | --- |
| 油冷回路 | 说明书 | |

## 七、和现有技术的差别

油冷通道 → 降低绕组温升
"""


def test_scan_and_payload() -> None:
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "MyVault"
        p = vault / "Research" / "Patents" / "车辆工程" / "CN119961390A" / "CN119961390A_解读_20260101.md"
        p.parent.mkdir(parents=True)
        p.write_text(_note("CN119961390A"), encoding="utf-8")
        recs = scan_vault(vault)
        assert len(recs) == 1
        assert recs[0]["filing_date"] == "2023-04-12"
        assert recs[0]["cited_pubs"] == ["CN114552122A"]
        assert recs[0]["terms"][0] == "油冷回路"
        assert recs[0]["means_effects"][0]["mean"] == "油冷通道"
        assert recs[0]["tech_effects"][0] == "降低绕组温升"
        payload = build_payload(vault)
        assert payload["vault_count"] == 1
        assert payload["count"] == 1
        assert payload["source"] == "vault"
        assert payload["patents"][0]["domain_id"] == domain_id_of("车辆工程")
        assert payload["domains"][0]["name"] == "车辆工程"
        assert payload["domains"][0]["count"] == 1
        assert payload["embedding"]["mode"] == "ipc"
        assert "x" not in payload["patents"][0]
        cache_dir = cache_dir_for_vault(vault)
        assert cache_dir == _TEST_MAP_HOME.resolve()
        assert vault not in cache_dir.parents
        assert cache_dir.parent.name != "MyVault"
        db = cache_db_path(vault)
        assert db.is_file()
        recs2 = scan_vault(vault)
        assert recs2[0]["one_liner"] == "油冷带走热量。"
        p.write_text(_note("CN119961390A").replace("油冷带走热量。", "结构改了。"), encoding="utf-8")
        recs3 = scan_vault(vault)
        assert recs3[0]["one_liner"] == "结构改了。"


def test_map_home_is_documents_skill_sibling_of_oa() -> None:
    old = os.environ.pop("PATENT_MAP_HOME", None)
    try:
        root = skill_data_root()
        assert root == (documents_dir() / "patent-disclosure-skill").resolve()
        home = map_home()
        assert home == (root / "patent-map").resolve()
        assert home.name == "patent-map"
    finally:
        if old is not None:
            os.environ["PATENT_MAP_HOME"] = old


def test_means_effects_skips_markdown_prose() -> None:
    body = """---
pub_number: CN120000002A
domain: 软件与互联网
---

# 专利解读：闭环

## 一、一句话

把痛点绑到成图。

## 七、和现有技术的差别

1. **墙到墙构建闭环**：知识库训模 → 把实测痛点数据绑定到成图环节并写进权利要求与说明书的实施步骤
2. **消解方式**：强调非衍生化溶剂分子级溶解
油冷通道 → 降低绕组温升
"""
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "MyVault"
        p = vault / "Research" / "Patents" / "软件" / "CN120000002A" / "CN120000002A_解读_20260101.md"
        p.parent.mkdir(parents=True)
        p.write_text(body, encoding="utf-8")
        recs = scan_vault(vault)
        assert recs[0]["means_effects"] == [
            {"mean": "油冷通道", "effect": "降低绕组温升", "source": "section7"}
        ]
        assert recs[0]["te_source"] == "section7"


def test_tech_effect_fallback_ipc_domain() -> None:
    body = """---
pub_number: CN120000003A
domain: 化工与材料
ipc: H01M50/446
ipc_codes:
  - H01M50/446
---

# 专利解读：旧笔记

## 一、一句话

涂层。

## 七、和现有技术的差别

1. **墙到墙构建闭环** → 把实测痛点数据绑定到成图环节并写进说明书
"""
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "MyVault"
        p = vault / "Research" / "Patents" / "化工" / "CN120000003A" / "CN120000003A_解读_20260101.md"
        p.parent.mkdir(parents=True)
        p.write_text(body, encoding="utf-8")
        recs = scan_vault(vault)
        assert recs[0]["te_source"] == "fallback"
        assert recs[0]["tech_means"] == []
        assert recs[0]["means_effects"] == [
            {"mean": "H01M", "effect": "化工与材料", "source": "fallback"}
        ]


def test_tech_effect_frontmatter_wins() -> None:
    body = """---
pub_number: CN120000001A
domain: 化工与材料
tech_means:
  - 湿法成膜
tech_effects:
  - 耐热
tech_effect_pairs:
  - 湿法成膜 → 耐热
---

# 专利解读：隔膜

## 一、一句话

涂层更牢。

## 七、和现有技术的差别

旧工艺 → 掉粉
"""
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "MyVault"
        p = vault / "Research" / "Patents" / "化工与材料" / "CN120000001A" / "CN120000001A_解读_20260101.md"
        p.parent.mkdir(parents=True)
        p.write_text(body, encoding="utf-8")
        recs = scan_vault(vault)
        assert recs[0]["tech_means"] == ["湿法成膜"]
        assert recs[0]["tech_effects"] == ["耐热"]
        assert recs[0]["means_effects"] == [
            {"mean": "湿法成膜", "effect": "耐热", "source": "agent"}
        ]
        assert recs[0]["te_source"] == "agent"


def test_domain_filter_keeps_catalog() -> None:
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "MyVault"
        a = vault / "Research" / "Patents" / "车辆工程" / "CN119961390A" / "CN119961390A_解读_20260101.md"
        b = vault / "Research" / "Patents" / "化工与材料" / "CN120000003A" / "CN120000003A_解读_20260101.md"
        a.parent.mkdir(parents=True)
        b.parent.mkdir(parents=True)
        a.write_text(_note("CN119961390A"), encoding="utf-8")
        b.write_text(
            _note("CN120000003A").replace("车辆工程", "化工与材料").replace("H02K9/19", "H01M50/446"),
            encoding="utf-8",
        )
        payload = build_payload(vault, embed=False)
        names = {d["name"] for d in payload["domains"]}
        assert names == {"车辆工程", "化工与材料"}
        assert payload["count"] == 2
        car = apply_domain_filter(payload, domain="车辆工程")
        assert car["count"] == 1
        assert car["patents"][0]["pub"] == "CN119961390A"
        assert {d["name"] for d in car["domains"]} == names
        by_id = apply_domain_filter(payload, domain_id=car["patents"][0]["domain_id"])
        assert by_id["count"] == 1
        empty = apply_domain_filter(payload, domain="不存在的领域")
        assert empty["count"] == 0
        assert empty["patents"] == []


def test_embed_text_and_pca() -> None:
    rec = {
        "invention_title": "一种油冷电机",
        "one_liner": "油冷带走热量。",
        "terms": ["油冷回路"],
        "means_effects": [{"mean": "油冷通道", "effect": "降低绕组温升"}],
        "domain": "车辆工程",
        "ipc": "H02K9/19",
    }
    text = compose_embed_text(rec)
    assert "油冷电机" in text
    assert "油冷回路" in text
    assert "降低绕组温升" in text
    xy = project_2d([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.95, 0.05, 0.0]])
    assert len(xy) == 3
    assert all(0.0 <= a <= 1.0 and 0.0 <= b <= 1.0 for a, b in xy)
    d02 = (xy[0][0] - xy[2][0]) ** 2 + (xy[0][1] - xy[2][1]) ** 2
    d01 = (xy[0][0] - xy[1][0]) ** 2 + (xy[0][1] - xy[1][1]) ** 2
    assert d02 < d01
    near = nearest_k([[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]], ["A", "B", "C"], k=1)
    assert near[0][0]["pub"] == "B"


def test_model_default_dir_not_cwd() -> None:
    old = os.environ.pop("PATENT_MAP_MODEL_DIR", None)
    try:
        d = default_model_dir()
        assert d == _TEST_MAP_HOME.resolve() / "models" / "bge-small-zh-v1.5"
        fake = Path(tempfile.mkdtemp()) / "bge-small-zh-v1.5"
        fake.mkdir(parents=True)
        (fake / "config.json").write_text("{}", encoding="utf-8")
        (fake / "tokenizer.json").write_text("{}", encoding="utf-8")
        (fake / "model_optimized.onnx").write_bytes(b"x" * 1_000_001)
        assert is_model_ready(fake)
        os.environ["PATENT_MAP_MODEL_DIR"] = str(fake)
        assert default_model_dir() == fake.resolve()
        hit = find_local_model(None)
        assert hit is not None
        assert hit.resolve() == fake.resolve()
    finally:
        if old is None:
            os.environ.pop("PATENT_MAP_MODEL_DIR", None)
        else:
            os.environ["PATENT_MAP_MODEL_DIR"] = old


def test_onnx_only_not_pytorch() -> None:
    assert HUB_ENDPOINTS == (
        "https://hf-mirror.com",
        "https://www.modelscope.cn/models",
        "https://huggingface.co",
    )
    pytorch_only = Path(tempfile.mkdtemp()) / "pt"
    pytorch_only.mkdir()
    (pytorch_only / "config.json").write_text("{}", encoding="utf-8")
    (pytorch_only / "tokenizer.json").write_text("{}", encoding="utf-8")
    (pytorch_only / "pytorch_model.bin").write_bytes(b"x" * 1_000_001)
    assert not is_model_ready(pytorch_only)
    safetensors = Path(tempfile.mkdtemp()) / "st"
    safetensors.mkdir()
    (safetensors / "config.json").write_text("{}", encoding="utf-8")
    (safetensors / "tokenizer.json").write_text("{}", encoding="utf-8")
    (safetensors / "model.safetensors").write_bytes(b"x" * 1_000_001)
    assert not is_model_ready(safetensors)


def test_random_port() -> None:
    MapHandler.vault = None
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), MapHandler)
    try:
        host, port = httpd.server_address
        assert host == "127.0.0.1"
        assert isinstance(port, int) and port > 0
    finally:
        httpd.server_close()


def test_chrome_probe_is_quiet_404() -> None:
    MapHandler.vault = None
    MapHandler.skip_embed = True
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), MapHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = httpd.server_address[1]
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=5)
            raise AssertionError("expected 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        assert body["ok"] is True
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_ipc_subclass_titles() -> None:
    assert resolve_ipc_csv().name == "ipc_subclasses_2026.01.csv"
    data = load_ipc_subclasses()
    assert data["version"] == "2026.01"
    assert data["count"] >= 600
    assert data["titles"]["H01M"] == "用于直接转变化学能为电能的方法或装置"
    assert data["titles"]["G06F"] == "电数字数据处理"
    assert data["titles"]["H02K"] == "电机"
    assert "NOPE" not in data["titles"]
    missing = load_ipc_subclasses(Path(tempfile.mkdtemp()) / "nope.csv")
    assert missing["titles"] == {}
    assert missing["count"] == 0

    MapHandler.vault = None
    MapHandler.skip_embed = True
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), MapHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = httpd.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ipc-subclasses", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        assert body["version"] == "2026.01"
        assert body["titles"]["H01M"] == data["titles"]["H01M"]
        assert body["count"] == data["count"]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_ipc_scheme_en_xml_fixture() -> None:
    xml = ROOT / "tools" / "ipc_scheme" / "testdata" / "sample_en_scheme.xml"
    titles = parse_en_xml(xml)
    assert titles["H01M"].startswith("PROCESSES OR MEANS")
    assert titles["H02K"] == "DYNAMO-ELECTRIC MACHINES"
    assert "H01" not in titles
    assert finalize_zh("H99Z", "anything") == "本部其他未列入的技术主题"
    assert finalize_zh("B29K", "foo") == "引得表"
    url = ipcpub_scheme_json_url("20260101", "20260806171617", "zh")
    assert url.endswith("/IPC/scheme/zh/json/index.json")
    zh = parse_ipcpub_json(ROOT / "tools" / "ipc_scheme" / "testdata" / "sample_ipcpub.json")
    assert zh["H01M"] == "用于直接转变化学能为电能的方法或装置"


if __name__ == "__main__":
    test_scan_and_payload()
    test_map_home_is_documents_skill_sibling_of_oa()
    test_means_effects_skips_markdown_prose()
    test_tech_effect_fallback_ipc_domain()
    test_tech_effect_frontmatter_wins()
    test_domain_filter_keeps_catalog()
    test_embed_text_and_pca()
    test_model_default_dir_not_cwd()
    test_onnx_only_not_pytorch()
    test_random_port()
    test_chrome_probe_is_quiet_404()
    test_ipc_subclass_titles()
    test_ipc_scheme_en_xml_fixture()
    print("OK patent-map")

"""IPC subclass table rebuild: versions, URLs, special codes."""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parents[1]
DEFAULT_CACHE = HERE / "cache"

# Human version vs WIPO folder date.
IPC_VERSION = "2026.01"
IPC_VERSION_DATE = "20260101"
DEFAULT_CSV = SKILL_ROOT / "data" / f"ipc_subclasses_{IPC_VERSION}.csv"

WIPO_IT_BASE = (
    "https://www.wipo.int/classifications/data/ipc/"
    f"ITSupport_and_download_area/{IPC_VERSION_DATE}"
)
WIPO_SCHEME_ZIP = f"{WIPO_IT_BASE}/MasterFiles/ipc_scheme_{IPC_VERSION_DATE}.zip"

IPCPUB_HOME = "https://ipcpub.wipo.int/"
IPCPUB_CDN = "https://cdn.ipcpub.wipo.int/media"

# Official Chinese table (links resolved from the page at build time).
CNIPA_TABLE_PAGE = "https://www.cnipa.gov.cn/art/2025/12/31/art_3161_203422.html"

# Used only if the notice page HTML cannot be parsed. Hashes are 2026.01-specific.
CNIPA_PDF_FALLBACK = {
    "A": "https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=2026.01%E7%89%88IPC%E5%88%86%E7%B1%BB%E8%A1%A8-A%E9%83%A8.pdf&filename=84f50032f9ce4301ab100f5c403e000b.pdf",
    "B": "https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=2026.01%E7%89%88IPC%E5%88%86%E7%B1%BB%E8%A1%A8-B%E9%83%A8.pdf&filename=a4f808817050429e849bd818907cfc1d.pdf",
    "C": "https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=2026.01%E7%89%88IPC%E5%88%86%E7%B1%BB%E8%A1%A8-C%E9%83%A8.pdf&filename=99c9d77c96ae4000ab1ec35c75a95881.pdf",
    "D": "https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=2026.01%E7%89%88IPC%E5%88%86%E7%B1%BB%E8%A1%A8-D%E9%83%A8.pdf&filename=7719d52ee72b4cedb8a925a86d8932cb.pdf",
    "E": "https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=2026.01%E7%89%88IPC%E5%88%86%E7%B1%BB%E8%A1%A8-E%E9%83%A8.pdf&filename=b5822d0c2cbc4daa823e95ebb9d70cd2.pdf",
    "F": "https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=2026.01%E7%89%88IPC%E5%88%86%E7%B1%BB%E8%A1%A8-F%E9%83%A8.pdf&filename=826c947f24cd469485b8c75e76b3226e.pdf",
    "G": "https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=2026.01%E7%89%88IPC%E5%88%86%E7%B1%BB%E8%A1%A8-G%E9%83%A8.pdf&filename=61ec0e15ff694bbc98f302ab0e4438ee.pdf",
    "H": "https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=2026.01%E7%89%88IPC%E5%88%86%E7%B1%BB%E8%A1%A8-H%E9%83%A8.pdf&filename=e68dc3300ca44d2d9e606a6a5c979725.pdf",
}

INDEXING_CODES = frozenset({"B29K", "B29L", "C10N", "C12R", "F21W", "F21Y"})
CATCHALL_SUFFIX = "99Z"
CATCHALL_TITLE = "本部其他未列入的技术主题"
INDEXING_TITLE = "引得表"

USER_AGENT = "patent-map-ipc-scheme/1.0 (+https://github.com/handsomestWei/patent-disclosure-skill)"

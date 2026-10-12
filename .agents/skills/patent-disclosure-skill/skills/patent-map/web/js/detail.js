/* 右侧详情与列表 */
function pushDetail() {
  const el = $("detail");
  if (el && el.innerHTML) detailStack.push(el.innerHTML);
}

function bindDetailNav() {
  const root = $("detail");
  if (!root) return;
  root.querySelectorAll("[data-pub]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const p = findPub(btn.dataset.pub);
      if (!p) return;
      pushDetail();
      showDetail(p, true);
    });
  });
  const back = root.querySelector("#detail-back");
  if (back) back.addEventListener("click", popDetail);
}

function popDetail() {
  const html = detailStack.pop();
  if (!html) return;
  $("detail").innerHTML = html;
  selected = "";
  bindDetailNav();
}

function detailBackBar() {
  return detailStack.length ? `<button type="button" class="detail-back" id="detail-back">← 返回</button>` : "";
}

function vaultFolderName() {
  const v = String(DATA.vault || "").replace(/\\/g, "/");
  const parts = v.split("/").filter(Boolean);
  return parts[parts.length - 1] || "";
}

function obsidianNoteHref(rel) {
  const name = vaultFolderName();
  if (!name || !rel) return "";
  const file = String(rel).replace(/\\/g, "/").replace(/\.md$/i, "");
  return `obsidian://open?vault=${encodeURIComponent(name)}&file=${encodeURIComponent(file)}`;
}

function noteLinks(rel) {
  if (!rel) return "";
  const label = escapeHtml(rel);
  const ob = obsidianNoteHref(rel);
  if (!ob) return `<p class="note-row">笔记 ${label}</p>`;
  return `<p class="note-row">笔记 <a class="note-app" href="${escapeHtml(ob)}">${label}</a></p>`;
}

function showDetail(p, keepStack) {
  if (!keepStack) detailStack = [];
  if (!p) {
    $("detail").innerHTML = domainFilter
      ? "<h2>该领域还没有已读专利</h2><p>换一个领域，或回到地形看全库沙盘。</p>"
      : "<h2>点一座山或一颗点</h2><p>高峰=库里语义相近的案子挤在一起。山谷只表示还没读到，不是行业空白。</p>";
    return;
  }
  selected = p.pub;
  selectedCluster = -1;
  const near = (p.nearest || [])
    .map((n) => {
      const hit = findPub(n.pub);
      const title = hit ? hit.invention_title || hit.title || n.pub : n.pub;
      const score = typeof n.score === "number" ? n.score.toFixed(2) : "";
      return `<button data-pub="${n.pub}">${n.pub} ${score} · ${plainText(title, 18)}</button>`;
    })
    .join("");
  $("detail").innerHTML = `
    ${detailBackBar()}
    <h2>${escapeHtml(p.pub)}</h2>
    <p>${mdInline(p.invention_title || p.title || "")}</p>
    <p>${mdInline(p.one_liner || "")}</p>
    <ul>
      <li>领域 ${escapeHtml(p.domain || "—")}</li>
      <li>IPC ${escapeHtml((p.ipc_codes || []).join("; ") || p.ipc || "—")}</li>
      <li>申请人 ${escapeHtml((p.assignees || []).join("、") || "—")}</li>
      <li>机构 ${escapeHtml((p.organizations || []).join("、") || "—")}</li>
      <li>发明人 ${escapeHtml((p.inventors || []).join("、") || "—")}</li>
      <li>申请日 ${escapeHtml(p.filing_date || "—")} · 公开日 ${escapeHtml(p.publication_date || "—")}</li>
      <li>技术手段 ${escapeHtml((p.tech_means || []).join("、") || "—")}</li>
      <li>技术功效 ${escapeHtml((p.tech_effects || []).join("、") || "—")}</li>
      ${
        p.te_source === "fallback"
          ? "<li>矩阵占位 IPC × 领域（笔记未写技术功效短标签）</li>"
          : ""
      }
      <li>引证 ${escapeHtml((p.cited_pubs || []).join("、") || "无")}</li>
    </ul>
    ${near ? `<p>语义近邻</p><div class="near">${near}</div>` : ""}
    ${noteLinks(p.note_path)}`;
  bindDetailNav();
  if (view === "terrain") render();
}

function showCluster(cl) {
  selectedCluster = cl.id;
  selected = "";
  detailStack = [];
  const btns = cl.members
    .map((n) => {
      const title = n.p.invention_title || n.p.title || n.p.pub;
      return `<button data-pub="${n.p.pub}">${n.p.pub} · ${plainText(title, 22)}</button>`;
    })
    .join("");
  $("detail").innerHTML = `
    <h2>山峰 · ${cl.label || "相近解读"}</h2>
    <p>库内 ${cl.members.length} 件挤在这一带。高峰只表示已读案子语义相近，不是检索热度。</p>
    <div class="near">${btns}</div>`;
  bindDetailNav();
  render();
}

function showMatrixCell(row, col, items) {
  selected = "";
  selectedCluster = -1;
  detailStack = [];
  if (!items.length) {
    const colLabel = ipcAxisLabel(col);
    $("detail").innerHTML = `<h2>${escapeHtml(row)} × ${escapeHtml(colLabel)}</h2><p>这一格还没有已读专利。</p>`;
    return;
  }
  const btns = items
    .map((p) => {
      const title = p.invention_title || p.title || p.pub;
      const mark = p.te_source === "fallback" ? " · 占位" : "";
      return `<button data-pub="${p.pub}">${p.pub} ${plainText(title, 22)}${mark}</button>`;
    })
    .join("");
  $("detail").innerHTML = `
    <h2>${escapeHtml(row)} × ${escapeHtml(ipcAxisLabel(col))}</h2>
    <div class="near">${btns}</div>`;
  bindDetailNav();
}

function showDashList(title, hint, items) {
  selected = "";
  selectedCluster = -1;
  detailStack = [];
  const btns = items
    .map((p) => {
      const name = p.invention_title || p.title || p.pub;
      return `<button data-pub="${p.pub}">${p.pub} · ${plainText(name, 22)}</button>`;
    })
    .join("");
  $("detail").innerHTML = `
    <h2>${title}</h2>
    <p>${hint} · 库内 ${items.length} 篇。</p>
    <div class="near">${btns}</div>`;
  bindDetailNav();
}

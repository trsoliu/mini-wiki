/* 顶栏：视图切换、领域过滤、GitHub 计数 */
function drawPills() {
  const domains = domainCatalog();
  const showFilter = ANALYZE_VIEWS.has(view) && domains.length >= 2;
  const opts = [`<option value="">全部领域</option>`]
    .concat(
      domains.map((d) => {
        const sel = d.id === domainFilter || d.name === domainFilter ? " selected" : "";
        return `<option value="${escapeHtml(d.id)}"${sel}>${escapeHtml(d.name)}（${d.count}）</option>`;
      })
    )
    .join("");
  $("pills").innerHTML =
    VIEWS.map((v) => `<button type="button" data-id="${v.id}" class="${v.id === view ? "active" : ""}">${v.name}</button>`).join("") +
    (showFilter
      ? `<label class="domain-filter">领域 <select id="domain-sel" aria-label="按领域过滤">${opts}</select></label>`
      : "");
  $("pills").onclick = (e) => {
    const btn = e.target.closest("button");
    const id = btn && btn.dataset.id;
    if (!id) return;
    if (id !== view) matrixDrill = null;
    view = id;
    drawPills();
    render();
  };
  const sel = $("domain-sel");
  if (sel) {
    sel.addEventListener("click", (e) => e.stopPropagation());
    sel.onchange = () => {
      domainFilter = sel.value;
      matrixDrill = null;
      dropOutsideFilter();
      resetCam();
      drawPills();
      render();
    };
  }
}

function formatCount(n) {
  if (!Number.isFinite(n)) return "";
  if (n >= 10000) return `${(n / 1000).toFixed(n % 1000 ? 1 : 0).replace(/\.0$/, "")}k`;
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, "")}k`;
  return String(n);
}

async function loadGithubMeta() {
  try {
    const res = await fetch("https://api.github.com/repos/handsomestWei/patent-disclosure-skill");
    if (!res.ok) return;
    const data = await res.json();
    const stars = formatCount(data.stargazers_count);
    const forks = formatCount(data.forks_count);
    if (stars && $("gh-star-label")) $("gh-star-label").textContent = stars;
    if (forks && $("gh-fork-label")) $("gh-fork-label").textContent = forks;
    if ($("gh-star") && data.stargazers_count) {
      $("gh-star").title = `${data.stargazers_count} stars`;
    }
  } catch (_) {
    /* 离线或 GitHub 不可达时仍保留仓库链接 */
  }
}

function yearSpanLabel(patents) {
  const years = patents
    .map(yearOf)
    .filter((y) => y !== "未标年")
    .map(Number)
    .filter((y) => y > 1900);
  if (!years.length) return "—";
  const min = Math.min(...years);
  const max = Math.max(...years);
  return min === max ? String(min) : `${min}–${max}`;
}

function renderMeta() {
  const n = DATA.patents.length;
  const emb = DATA.embedding || {};
  $("stats").innerHTML = `
    <div class="stat"><strong>${domainCatalog().length}</strong><span>领域数</span></div>
    <div class="stat"><strong>${n}</strong><span>专利数</span></div>
    <div class="stat"><strong>${yearSpanLabel(DATA.patents)}</strong><span>年份跨度</span></div>`;
  const banner = $("banner");
  if (emb.available) {
    banner.hidden = true;
    banner.textContent = "";
  } else if (n > 0 && emb.error && emb.error !== "skipped" && emb.error !== "empty") {
    banner.hidden = false;
    banner.textContent = "语义地形未启用，已用 IPC 簇顶上。" + (emb.error ? ` ${emb.error}` : "");
  } else {
    banner.hidden = true;
  }
}

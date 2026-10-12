/* 视图调度与启动 */
function render() {
  const stage = $("stage");
  const relief = $("relief");
  const sandbox = view === "terrain";
  if (stage) stage.classList.toggle("sandbox", sandbox);
  const gl3d = $("gl3d");
  if (!sandbox) {
    if (relief) {
      relief.hidden = true;
      const ctx = relief.getContext("2d");
      ctx.clearRect(0, 0, relief.width, relief.height);
    }
    if (gl3d) gl3d.hidden = true;
  }
  const viewChanged = lastView !== view;
  lastView = view;
  if (viewChanged) {
    resetCam();
    detailStack = [];
    dashScroll.x = 0;
    matrixDrill = null;
  }
  else applyCam();
  ({
    terrain: renderTerrain,
    bubble: renderBubble,
    citation: renderCitation,
    matrix: renderMatrix,
    dashboard: renderDashboard,
  })[view]();
  renderMeta();
  if (viewChanged) {
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        if (view === "matrix" || view === "dashboard") resetCam();
        else fitCam();
      })
    );
  }
  const pool = view === "terrain" ? DATA.patents : viewPatents();
  if (!matrixDrill && !selected && selectedCluster < 0) showDetail(pool[0] || null);
}

async function boot() {
  drawPills();
  bindCam();
  loadGithubMeta();
  try {
    const ipcPromise = fetch("/api/ipc-subclasses")
      .then((r) => (r.ok ? r.json() : { titles: {} }))
      .catch(() => ({ titles: {} }));
    const res = await fetch("/api/patents");
    DATA = await res.json();
    if (!Array.isArray(DATA.patents)) DATA.patents = [];
    if (!Array.isArray(DATA.domains)) DATA.domains = [];
    const ipc = await ipcPromise;
    DATA.ipc_titles = ipc.titles || {};
    DATA.ipc_version = ipc.version || "";
  } catch (e) {
    const banner = $("banner");
    if (banner) {
      banner.hidden = false;
      banner.textContent = "读接口失败：" + e;
    }
    return;
  }
  drawPills();
  renderMeta();
  render();
}

boot();

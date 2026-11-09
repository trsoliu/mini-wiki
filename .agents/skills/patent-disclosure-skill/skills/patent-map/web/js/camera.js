/* 平移缩放、仪表盘横向滚动、3D 轨道 */
const CAM_MIN = 0.35;
const CAM_MAX = 4.2;
let camUserMoved = false;
let dashScroll = {
  x: 0,
  max: 0,
  vis: 444,
  content: 444,
  active: false,
  x0: 56,
  x1: 500,
  y0: 28,
  y1: 460,
};
let dashDrag = null;

function inDashBarArea(pt) {
  return (
    pt.x >= dashScroll.x0 &&
    pt.x <= dashScroll.x1 &&
    pt.y >= dashScroll.y0 &&
    pt.y <= dashScroll.y1
  );
}

function setDashScroll(x) {
  const max = dashScroll.max;
  dashScroll.x = max <= 0 ? 0 : Math.max(0, Math.min(max, x));
  applyDashScroll();
}

function applyDashScroll() {
  const g = $("dash-bars");
  if (g) g.setAttribute("transform", `translate(${-dashScroll.x},0)`);
  const thumb = $("dash-thumb");
  if (!thumb || dashScroll.max <= 0) return;
  const trackW = dashScroll.vis;
  const thumbW = Math.max(28, (dashScroll.vis / Math.max(dashScroll.content, 1)) * trackW);
  const room = Math.max(trackW - thumbW, 1);
  thumb.setAttribute("x", String(dashScroll.x0 + (dashScroll.x / dashScroll.max) * room));
  thumb.setAttribute("width", String(thumbW));
}

function clientToSvgDx(svg, dxPx) {
  const w = svg && svg.clientWidth ? svg.clientWidth : MAP_W;
  return dxPx * (MAP_W / w);
}

function applyCam() {
  const cam = $("cam");
  if (!cam) return;
  cam.style.transformOrigin = "0 0";
  cam.style.transform = `translate(${camState.x}px, ${camState.y}px) scale(${camState.k})`;
}

function resetCam() {
  camState = { k: 1, x: 0, y: 0 };
  camUserMoved = false;
  applyCam();
  if (window.Terrain3D) {
    Terrain3D.reset();
    if (view === "terrain" && Terrain3D.ready()) {
      Terrain3D.render();
      syncTerrainSvg();
    }
  }
}

function zoomAt(mx, my, factor) {
  const nk = Math.max(CAM_MIN, Math.min(CAM_MAX, camState.k * factor));
  if (nk === camState.k) return;
  const nx = (mx - camState.x) / camState.k;
  const ny = (my - camState.y) / camState.k;
  camState.k = nk;
  camState.x = mx - nx * nk;
  camState.y = my - ny * nk;
  camUserMoved = true;
  applyCam();
}

function focusUser(ux, uy, k) {
  const vp = $("viewport");
  if (!vp) return;
  const vw = vp.clientWidth;
  const vh = vp.clientHeight;
  if (!vw || !vh) return;
  camState.k = Math.max(CAM_MIN, Math.min(CAM_MAX, k));
  camState.x = vw / 2 - (ux / MAP_W) * vw * camState.k;
  camState.y = vh / 2 - (uy / MAP_H) * vh * camState.k;
  camUserMoved = true;
  applyCam();
}

function fitCam() {
  // SVG 已 width/height:100% 铺满视口，viewBox 由浏览器 contain。
  // 不能用 getBBox：轴标签溢出 960×520 后框会虚大，相机会缩到 CAM_MIN（图只剩一小块）。
  resetCam();
}

function isCamHitTarget(el) {
  if (!el || el.id === "viewport" || el.id === "cam" || el.id === "chart") return false;
  const tag = el.tagName;
  if (tag === "circle" || tag === "text" || tag === "ellipse") return true;
  if (tag === "rect" && el.style.cursor === "pointer") return true;
  return false;
}

function bindCam() {
  const vp = $("viewport");
  const svg = $("chart");
  if (!vp || vp.dataset.bound) return;
  vp.dataset.bound = "1";
  vp.addEventListener(
    "wheel",
    (e) => {
      if (view === "dashboard" && dashScroll.active) {
        const pt = svgPoint(svg, e);
        if (inDashBarArea(pt) || (e.target && (e.target.id === "dash-thumb" || e.target.id === "dash-track"))) {
          e.preventDefault();
          const raw = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
          setDashScroll(dashScroll.x + clientToSvgDx(svg, raw));
          return;
        }
      }
      if (view === "terrain" && useTerrain3D()) {
        e.preventDefault();
        Terrain3D.dolly(e.deltaY > 0 ? 1.08 : 1 / 1.08);
        Terrain3D.render();
        syncTerrainSvg();
        return;
      }
      e.preventDefault();
      const r = vp.getBoundingClientRect();
      zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY > 0 ? 0.9 : 1.12);
    },
    { passive: false }
  );
  let drag = null;
  vp.addEventListener("pointerdown", (e) => {
    if (e.button != null && e.button !== 0) return;
    if (view === "dashboard" && dashScroll.active) {
      const pt = svgPoint(svg, e);
      const onThumb = e.target && e.target.id === "dash-thumb";
      const onTrack = e.target && e.target.id === "dash-track";
      if (onThumb || onTrack || inDashBarArea(pt)) {
        if (onTrack && !onThumb) {
          const frac = (pt.x - dashScroll.x0) / Math.max(dashScroll.vis, 1);
          setDashScroll(frac * dashScroll.max - dashScroll.vis * 0.15);
        }
        dashDrag = {
          sx: e.clientX,
          pan: dashScroll.x,
          moved: false,
          thumb: onThumb,
        };
        vp.classList.add("is-drag");
        vp.setPointerCapture(e.pointerId);
        return;
      }
    }
    if (view === "terrain" && useTerrain3D() && !isCamHitTarget(e.target)) {
      drag = { kind: "orbit", sx: e.clientX, sy: e.clientY, moved: false };
      vp.classList.add("is-drag");
      vp.setPointerCapture(e.pointerId);
      return;
    }
    if (isCamHitTarget(e.target)) return;
    drag = { kind: "pan", x: e.clientX - camState.x, y: e.clientY - camState.y, sx: e.clientX, sy: e.clientY, moved: false };
    vp.classList.add("is-drag");
    vp.setPointerCapture(e.pointerId);
  });
  vp.addEventListener("pointermove", (e) => {
    if (dashDrag) {
      if (Math.abs(e.clientX - dashDrag.sx) > 4) dashDrag.moved = true;
      const dx = clientToSvgDx(svg, e.clientX - dashDrag.sx);
      if (dashDrag.thumb) {
        const room = Math.max(dashScroll.vis - Math.max(28, (dashScroll.vis / Math.max(dashScroll.content, 1)) * dashScroll.vis), 1);
        setDashScroll(dashDrag.pan + (dx / room) * dashScroll.max);
      } else {
        setDashScroll(dashDrag.pan - dx);
      }
      return;
    }
    if (drag && drag.kind === "orbit") {
      const dx = e.clientX - drag.sx;
      const dy = e.clientY - drag.sy;
      if (Math.hypot(dx, dy) > 4) drag.moved = true;
      Terrain3D.orbit(dx * 0.008, dy * 0.006);
      drag.sx = e.clientX;
      drag.sy = e.clientY;
      Terrain3D.render();
      syncTerrainSvg();
      return;
    }
    if (!drag) return;
    if (Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) > 4) drag.moved = true;
    camState.x = e.clientX - drag.x;
    camState.y = e.clientY - drag.y;
    if (drag.moved) camUserMoved = true;
    applyCam();
  });
  vp.addEventListener("pointerup", (e) => {
    if (dashDrag) {
      const moved = dashDrag.moved;
      dashDrag = null;
      vp.classList.remove("is-drag");
      if (moved) {
        const stop = (ev) => {
          ev.stopPropagation();
          ev.preventDefault();
        };
        vp.addEventListener("click", stop, { capture: true, once: true });
      }
      return;
    }
    const moved = drag && drag.moved;
    drag = null;
    vp.classList.remove("is-drag");
    if (moved || view !== "terrain") return;
    const pt = svgPoint($("chart"), e);
    let best = null;
    let bestD = 16 * 16;
    TERRAIN.pts.forEach((n) => {
      const d = (n.px - pt.x) ** 2 + (n.py - pt.y) ** 2;
      if (d < bestD) {
        bestD = d;
        best = n;
      }
    });
    if (best) {
      showDetail(best.p);
      return;
    }
    const cl = TERRAIN.clusters.find((c) => (c.px - pt.x) ** 2 + (c.py - pt.y) ** 2 < 72 * 72);
    if (cl) showCluster(cl);
  });
  vp.addEventListener("pointercancel", () => {
    drag = null;
    dashDrag = null;
    vp.classList.remove("is-drag");
  });
  if (svg && !svg.dataset.focusBound) {
    svg.dataset.focusBound = "1";
    svg.addEventListener("dblclick", (e) => {
      e.preventDefault();
      const t = e.target;
      if (t && (t.tagName === "circle" || t.tagName === "ellipse")) {
        const cx = +t.getAttribute("cx");
        const cy = +t.getAttribute("cy");
        if (Number.isFinite(cx) && Number.isFinite(cy)) {
          focusUser(cx, cy, Math.min(CAM_MAX, Math.max(1.7, camState.k * 1.55)));
          return;
        }
      }
      fitCam();
    });
  }
  const zoomCenter = (factor) => {
    if (view === "terrain" && useTerrain3D()) {
      Terrain3D.dolly(1 / factor);
      Terrain3D.render();
      syncTerrainSvg();
      return;
    }
    zoomAt(vp.clientWidth / 2, vp.clientHeight / 2, factor);
  };
  if ($("zoom-in")) $("zoom-in").onclick = () => zoomCenter(1.22);
  if ($("zoom-out")) $("zoom-out").onclick = () => zoomCenter(1 / 1.22);
  if ($("zoom-fit")) $("zoom-fit").onclick = () => (view === "terrain" && window.Terrain3D ? resetCam() : fitCam());
  if ($("zoom-reset")) $("zoom-reset").onclick = () => resetCam();
  window.addEventListener("resize", () => {
    if (view === "terrain" && useTerrain3D()) {
      Terrain3D.resize();
      Terrain3D.render();
      syncTerrainSvg();
    } else if (!camUserMoved) fitCam();
  });
}

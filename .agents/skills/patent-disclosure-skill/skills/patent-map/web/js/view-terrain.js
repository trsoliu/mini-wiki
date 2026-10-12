/* 地形沙盘：语义密度 + IPC 簇 */
function mixStops(t) {
  t = Math.max(0, Math.min(1, t));
  for (let i = 1; i < TERRAIN_STOPS.length; i++) {
    if (t <= TERRAIN_STOPS[i][0]) {
      const [t0, c0] = TERRAIN_STOPS[i - 1];
      const [t1, c1] = TERRAIN_STOPS[i];
      const u = (t - t0) / (t1 - t0 || 1);
      return c0.map((v, k) => Math.round(v + (c1[k] - v) * u));
    }
  }
  return TERRAIN_STOPS[TERRAIN_STOPS.length - 1][1];
}

function rgb(c, a) {
  return a == null ? `rgb(${c[0]},${c[1]},${c[2]})` : `rgba(${c[0]},${c[1]},${c[2]},${a})`;
}

function projectIsoRaw(x, y, z) {
  return {
    x: x + (y - MAP_H / 2) * 0.2,
    y: y * 0.58 - z * 42,
  };
}

let PROJECT = (x, y, z) => projectIsoRaw(x, y, z);

function makeProjector(field) {
  const { grid, cols, rows, cw, ch } = field;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (let r = 0; r <= rows; r++) {
    for (let c = 0; c <= cols; c++) {
      const p = projectIsoRaw(c * cw, r * ch, grid[r][c]);
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x);
      maxY = Math.max(maxY, p.y);
    }
  }
  const s = Math.min((MAP_W - 56) / (maxX - minX || 1), (MAP_H - 48) / (maxY - minY || 1));
  const ox = (MAP_W - (maxX - minX) * s) / 2 - minX * s;
  const oy = (MAP_H - (maxY - minY) * s) / 2 - minY * s;
  return (x, y, z) => {
    const p = projectIsoRaw(x, y, z);
    return { x: p.x * s + ox, y: p.y * s + oy };
  };
}

function densityField(pts, cols, rows, w, h, sigma) {
  const cw = w / cols;
  const ch = h / rows;
  const grid = [];
  let maxD = 1e-6;
  for (let r = 0; r <= rows; r++) {
    grid[r] = [];
    for (let c = 0; c <= cols; c++) {
      const x = c * cw;
      const y = r * ch;
      let d = 0;
      for (const p of pts) {
        const dx = p.x - x;
        const dy = p.y - y;
        d += Math.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma));
      }
      grid[r][c] = d;
      if (d > maxD) maxD = d;
    }
  }
  for (let r = 0; r <= rows; r++) {
    for (let c = 0; c <= cols; c++) grid[r][c] /= maxD;
  }
  return { grid, cols, rows, cw, ch, w, h };
}

function densityAt(field, x, y) {
  const c = x / field.cw;
  const r = y / field.ch;
  const c0 = Math.max(0, Math.min(field.cols - 1, Math.floor(c)));
  const r0 = Math.max(0, Math.min(field.rows - 1, Math.floor(r)));
  const c1 = Math.min(field.cols, c0 + 1);
  const r1 = Math.min(field.rows, r0 + 1);
  const u = Math.max(0, Math.min(1, c - c0));
  const v = Math.max(0, Math.min(1, r - r0));
  const g = field.grid;
  return (
    g[r0][c0] * (1 - u) * (1 - v) +
    g[r0][c1] * u * (1 - v) +
    g[r1][c0] * (1 - u) * v +
    g[r1][c1] * u * v
  );
}

function contourSegments(field, level) {
  const segs = [];
  const { grid, cols, rows, cw, ch } = field;
  const lerp = (a, b, va, vb) => {
    if (Math.abs(vb - va) < 1e-6) return (a + b) / 2;
    return a + ((level - va) / (vb - va)) * (b - a);
  };
  const table = {
    1: [[3, 0]],
    2: [[0, 1]],
    3: [[3, 1]],
    4: [[1, 2]],
    5: [[3, 0], [1, 2]],
    6: [[0, 2]],
    7: [[3, 2]],
    8: [[2, 3]],
    9: [[0, 2]],
    10: [[0, 1], [2, 3]],
    11: [[1, 2]],
    12: [[1, 3]],
    13: [[0, 1]],
    14: [[0, 3]],
  };
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const x = c * cw;
      const y = r * ch;
      const v = [grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]];
      const idx =
        (v[0] >= level ? 1 : 0) |
        (v[1] >= level ? 2 : 0) |
        (v[2] >= level ? 4 : 0) |
        (v[3] >= level ? 8 : 0);
      if (!table[idx]) continue;
      const edge = (e) => {
        if (e === 0) return [lerp(x, x + cw, v[0], v[1]), y];
        if (e === 1) return [x + cw, lerp(y, y + ch, v[1], v[2])];
        if (e === 2) return [lerp(x, x + cw, v[3], v[2]), y + ch];
        return [x, lerp(y, y + ch, v[0], v[3])];
      };
      table[idx].forEach(([a, b]) => segs.push([edge(a), edge(b)]));
    }
  }
  return segs;
}

function drawSand(canvas, field) {
  const ctx = canvas.getContext("2d");
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = MAP_W * dpr;
  canvas.height = MAP_H * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, MAP_W, MAP_H);
  ctx.fillStyle = "#efece6";
  ctx.fillRect(0, 0, MAP_W, MAP_H);
  const { grid, cols, rows, cw, ch } = field;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const z00 = grid[r][c];
      const z10 = grid[r][c + 1];
      const z01 = grid[r + 1][c];
      const z11 = grid[r + 1][c + 1];
      const z = (z00 + z10 + z01 + z11) / 4;
      const x = c * cw;
      const y = r * ch;
      const p00 = PROJECT(x, y, z00);
      const p10 = PROJECT(x + cw, y, z10);
      const p11 = PROJECT(x + cw, y + ch, z11);
      const p01 = PROJECT(x, y + ch, z01);
      const shade = 0.78 + (z10 - z00) * 0.9 - (z01 - z00) * 1.1;
      const base = mixStops(z);
      const col = base.map((v) => Math.max(0, Math.min(255, Math.round(v * shade))));
      ctx.beginPath();
      ctx.moveTo(p00.x, p00.y);
      ctx.lineTo(p10.x, p10.y);
      ctx.lineTo(p11.x, p11.y);
      ctx.lineTo(p01.x, p01.y);
      ctx.closePath();
      ctx.fillStyle = rgb(col);
      ctx.fill();
    }
  }
  [0.22, 0.4, 0.58, 0.74, 0.88].forEach((level, i) => {
    ctx.strokeStyle = `rgba(20, 20, 31, ${0.12 + i * 0.05})`;
    ctx.lineWidth = i >= 3 ? 1.15 : 0.9;
    ctx.beginPath();
    contourSegments(field, level).forEach(([a, b]) => {
      const pa = PROJECT(a[0], a[1], level);
      const pb = PROJECT(b[0], b[1], level);
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
    });
    ctx.stroke();
  });
}

function clusterPeaks(field, pts) {
  const { grid, cols, rows, cw, ch } = field;
  const raw = [];
  for (let r = 1; r < rows; r++) {
    for (let c = 1; c < cols; c++) {
      const v = grid[r][c];
      if (v < 0.32) continue;
      let peak = true;
      for (let dr = -1; dr <= 1 && peak; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
          if (grid[r + dr][c + dc] > v + 1e-6) peak = false;
        }
      }
      if (peak) raw.push({ x: c * cw, y: r * ch, z: v });
    }
  }
  raw.sort((a, b) => b.z - a.z);
  const kept = [];
  raw.forEach((p) => {
    if (kept.some((k) => (k.x - p.x) ** 2 + (k.y - p.y) ** 2 < 88 * 88)) return;
    kept.push(p);
  });
  return kept.map((pk, i) => {
    const members = pts.filter((n) => (n.x - pk.x) ** 2 + (n.y - pk.y) ** 2 < 120 * 120);
    const tally = {};
    members.forEach((m) => {
      const d = m.p.domain || "未分类";
      tally[d] = (tally[d] || 0) + 1;
    });
    const label = Object.entries(tally).sort((a, b) => b[1] - a[1])[0]?.[0] || "";
    const pr = PROJECT(pk.x, pk.y, pk.z);
    return { id: i, ...pk, px: pr.x, py: pr.y, members, label };
  }).filter((c) => c.members.length);
}

function valleySpot(field, clusters) {
  const { grid, cols, rows, cw, ch } = field;
  let best = null;
  let bestV = 1;
  for (let r = 4; r < rows - 3; r += 2) {
    for (let c = 4; c < cols - 3; c += 2) {
      const v = grid[r][c];
      if (v > 0.18 || v >= bestV) continue;
      const x = c * cw;
      const y = r * ch;
      if (clusters.some((cl) => (cl.x - x) ** 2 + (cl.y - y) ** 2 < 160 * 160)) continue;
      bestV = v;
      best = { x, y, z: v };
    }
  }
  return best;
}

function useTerrain3D() {
  return !!(window.Terrain3D && Terrain3D.ready());
}

function syncTerrainSvg() {
  if (!useTerrain3D() || !TERRAIN.pts) return;
  TERRAIN.pts.forEach((n) => {
    const pr = Terrain3D.worldToScreen(n.x, n.y, n.z);
    n.px = pr.x;
    n.py = pr.y;
    if (n.el) {
      n.el.setAttribute("cx", String(pr.x));
      n.el.setAttribute("cy", String(pr.y));
      n.el.setAttribute("opacity", pr.behind ? "0.2" : "1");
    }
  });
  (TERRAIN.clusters || []).forEach((cl) => {
    const pr = Terrain3D.worldToScreen(cl.x, cl.y, cl.z);
    cl.px = pr.x;
    cl.py = pr.y;
    const n = cl.members.length;
    const ry = 26 + Math.min(n, 6) * 3;
    (cl.els || []).forEach((el, i) => {
      const s = [1, 0.72, 0.44][i] || 1;
      el.setAttribute("cx", String(pr.x));
      el.setAttribute("cy", String(pr.y - (1 - s) * 5));
    });
    if (cl.labelEl) {
      cl.labelEl.setAttribute("x", String(pr.x - 28));
      cl.labelEl.setAttribute("y", String(pr.y - ry - 10));
    }
  });
  if (TERRAIN.valley && TERRAIN.valleyEl) {
    const pr = Terrain3D.worldToScreen(TERRAIN.valley.x, TERRAIN.valley.y, TERRAIN.valley.z);
    TERRAIN.valleyEl.setAttribute("x", String(pr.x - 28));
    TERRAIN.valleyEl.setAttribute("y", String(pr.y));
  }
}

function renderTerrainSemantic(svg) {
  const pad = 56;
  const pts = DATA.patents.map((p) => {
    const xy = mapPoint(p, MAP_W, MAP_H, pad);
    return { ...xy, p };
  });
  const n = pts.length;
  const sigma = n < 8 ? 92 : n < 20 ? 78 : 64;
  const field = densityField(pts, 48, 26, MAP_W, MAP_H, sigma);
  const gl3d = $("gl3d");
  const relief = $("relief");
  let glOn = false;
  if (window.Terrain3D && gl3d && Terrain3D.init(gl3d)) glOn = Terrain3D.setField(field);
  if (glOn) {
    if (relief) relief.hidden = true;
    gl3d.hidden = false;
    Terrain3D.resize();
    Terrain3D.render();
    PROJECT = (x, y, z) => Terrain3D.worldToScreen(x, y, z);
  } else {
    if (gl3d) gl3d.hidden = true;
    if (relief) relief.hidden = false;
    PROJECT = makeProjector(field);
    drawSand(relief, field);
  }
  const clusters = clusterPeaks(field, pts);
  pts.forEach((node) => {
    const z = densityAt(field, node.x, node.y);
    const pr = PROJECT(node.x, node.y, z);
    node.z = z;
    node.px = pr.x;
    node.py = pr.y;
  });
  TERRAIN = { pts, clusters, field };

  clusters.forEach((cl, idx) => {
    const on = cl.id === selectedCluster;
    const peak = idx === 0;
    const n = cl.members.length;
    const rx = 50 + Math.min(n, 6) * 6;
    const ry = 26 + Math.min(n, 6) * 3;
    cl.els = [];
    [
      [1, "#d8d6d0", 0.42],
      [0.72, "#c4c2bc", 0.5],
      [0.44, peak ? "#5b92d9" : "#b0aead", peak ? 0.88 : 0.7],
    ].forEach(([s, fill, op]) => {
      const ring = svgEl("ellipse", {
        cx: cl.px,
        cy: cl.py - (1 - s) * 5,
        rx: rx * s,
        ry: ry * s,
        fill,
        opacity: String(op),
        stroke: "#14141f",
        "stroke-opacity": on ? "0.45" : "0.14",
        "stroke-width": on ? "2" : "1",
      });
      ring.style.cursor = "pointer";
      ring.addEventListener("click", (e) => {
        e.stopPropagation();
        showCluster(cl);
      });
      cl.els.push(ring);
      svg.appendChild(ring);
    });
    const t = svgEl("text", { x: cl.px - 28, y: cl.py - ry - 10, class: "peak-label" });
    t.textContent = cl.label;
    cl.labelEl = t;
    svg.appendChild(t);
  });

  const valley = valleySpot(field, clusters);
  if (valley && clusters.length) {
    const pr = PROJECT(valley.x, valley.y, valley.z);
    const t = svgEl("text", { x: pr.x - 28, y: pr.y, class: "valley-label" });
    t.textContent = "库内稀疏";
    svg.appendChild(t);
    TERRAIN.valley = valley;
    TERRAIN.valleyEl = t;
  }

  pts.forEach((n) => {
    const sel = n.p.pub === selected;
    const c = svgEl("circle", {
      cx: n.px,
      cy: n.py,
      r: sel ? 7 : 4.5,
      fill: "#1b1b1f",
      stroke: sel ? "#2d6cb5" : "#f7f5ef",
      "stroke-width": sel ? "3" : "1.4",
      class: sel ? "sel" : "",
      "data-pub": n.p.pub,
    });
    c.style.cursor = "pointer";
    const title = svgEl("title", {});
    title.textContent = `${n.p.pub} ${n.p.invention_title || n.p.title || ""}`;
    c.appendChild(title);
    c.addEventListener("click", (e) => {
      e.stopPropagation();
      showDetail(n.p);
    });
    n.el = c;
    svg.appendChild(c);
  });

  TERRAIN = { pts, clusters, field, valley: TERRAIN.valley, valleyEl: TERRAIN.valleyEl };

  $("legend").innerHTML =
    `<span>谷</span><span><i class="bar"></i></span><span>峰</span>` +
    (glOn
      ? `<span>点=已读专利 · 拖拽旋转 · 滚轮拉近</span>`
      : `<span>点=已读专利 · 刷山看簇</span>`);
}

function renderTerrainIpc(svg) {
  const relief = $("relief");
  if (relief) {
    const ctx = relief.getContext("2d");
    relief.width = MAP_W;
    relief.height = MAP_H;
    ctx.fillStyle = "#efece6";
    ctx.fillRect(0, 0, MAP_W, MAP_H);
  }
  const groups = {};
  DATA.patents.forEach((p) => {
    const k = ipcPrefix(p);
    (groups[k] ||= []).push(p);
  });
  const keys = Object.keys(groups);
  const ranked = keys.slice().sort((a, b) => groups[b].length - groups[a].length);
  keys.forEach((k, i) => {
    const cx = 150 + (i % 4) * 220;
    const cy = 150 + Math.floor(i / 4) * 190;
    const n = groups[k].length;
    const peak = k === ranked[0];
    [
      [1, "#d8d6d0", 0.95],
      [0.72, "#c4c2bc", 0.9],
      [0.46, peak ? "#5b92d9" : "#b8b6b0", peak ? 0.95 : 0.85],
    ].forEach(([s, fill, op]) => {
      svg.appendChild(
        svgEl("ellipse", {
          cx,
          cy: cy - (1 - s) * 6,
          rx: (48 + n * 10) * s,
          ry: (28 + n * 6) * s,
          fill,
          opacity: String(op),
          stroke: "#14141f",
          "stroke-opacity": "0.12",
        })
      );
    });
    groups[k].forEach((p, j) => {
      const a = (j / Math.max(n, 1)) * Math.PI * 2;
      const x = cx + Math.cos(a) * (16 + n * 4);
      const y = cy + Math.sin(a) * (9 + n * 2);
      const c = svgEl("circle", {
        cx: x,
        cy: y,
        r: 4.5,
        fill: "#1b1b1f",
        stroke: "#f7f5ef",
        "stroke-width": "1.2",
        "data-pub": p.pub,
      });
      c.style.cursor = "pointer";
      c.addEventListener("click", () => showDetail(p));
      svg.appendChild(c);
    });
    const t = svgEl("text", { x: cx - 28, y: cy - 44, class: "peak-label" });
    t.textContent = `${k} · ${n}`;
    svg.appendChild(t);
  });
  $("legend").innerHTML =
    '<span>按 IPC 前四位堆山（语义模型未就绪）</span><span>谷</span><span><i class="bar"></i></span><span>峰</span>';
}

function renderTerrain() {
  const svg = clearSvg();
  if (hasSemantic()) renderTerrainSemantic(svg);
  else {
    const gl3d = $("gl3d");
    if (gl3d) gl3d.hidden = true;
    const relief = $("relief");
    if (relief) relief.hidden = false;
    renderTerrainIpc(svg);
  }
}

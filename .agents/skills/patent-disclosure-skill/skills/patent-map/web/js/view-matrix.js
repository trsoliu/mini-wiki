/* 技术功效矩阵：先 IPC（× 领域），再下钻手段×功效稀疏气泡 */
const MATRIX_MAX_R = 14;
const MATRIX_MAX_C = 12;
const MATRIX_TOP_N = 8;

function pushToCell(cell, key, p) {
  if (!(cell[key] || []).some((x) => x.pub === p.pub)) (cell[key] ||= []).push(p);
}

function rankKeys(counts) {
  return Object.keys(counts).sort((a, b) => counts[b] - counts[a] || a.localeCompare(b, "zh"));
}

function lumpKeys(counts, limit) {
  const keys = rankKeys(counts);
  if (keys.length <= limit) {
    const map = {};
    keys.forEach((k) => {
      map[k] = k;
    });
    return { keys, map, extra: 0 };
  }
  const keep = keys.slice(0, Math.max(1, limit - 1));
  const map = {};
  keep.forEach((k) => {
    map[k] = k;
  });
  keys.slice(keep.length).forEach((k) => {
    map[k] = AXIS_OTHER;
  });
  return { keys: keep.concat([AXIS_OTHER]), map, extra: keys.length - keep.length };
}

function remapCells(cell, rowMap, colMap) {
  const out = {};
  Object.entries(cell).forEach(([k, items]) => {
    const parts = k.split("||");
    const nr = rowMap[parts[0]] || parts[0];
    const nc = colMap[parts[1]] || parts[1];
    const nk = nr + "||" + nc;
    items.forEach((p) => pushToCell(out, nk, p));
  });
  return out;
}

function ipcDomainCells(patents) {
  const byRow = {};
  const byCol = {};
  const cell = {};
  patents.forEach((p) => {
    const domain = p.domain || "未分类";
    ipcPrefixesOf(p).forEach((ipc) => {
      byRow[domain] = (byRow[domain] || 0) + 1;
      byCol[ipc] = (byCol[ipc] || 0) + 1;
      pushToCell(cell, domain + "||" + ipc, p);
    });
  });
  return { byRow, byCol, cell };
}

function ipcCells(patents) {
  const byCol = {};
  const cell = {};
  patents.forEach((p) => {
    ipcPrefixesOf(p).forEach((ipc) => {
      byCol[ipc] = (byCol[ipc] || 0) + 1;
      pushToCell(cell, "本领域||" + ipc, p);
    });
  });
  return { byRow: { 本领域: patents.length }, byCol, cell };
}

function teCells(patents) {
  const byRow = {};
  const byCol = {};
  const cell = {};
  let labeled = 0;
  patents.forEach((p) => {
    const pairs = tePairs(p);
    if (!pairs.length) return;
    labeled += 1;
    pairs.forEach((me) => {
      byRow[me.mean] = (byRow[me.mean] || 0) + 1;
      byCol[me.effect] = (byCol[me.effect] || 0) + 1;
      pushToCell(cell, me.mean + "||" + me.effect, p);
    });
  });
  return { byRow, byCol, cell, labeled };
}

function axisChars(px) {
  return Math.max(3, Math.floor(Math.max(px, 24) / 12));
}

function wrapTwoLines(s, maxChars) {
  const t = cleanTeLabel(s);
  const n = Math.max(2, maxChars);
  if (t.length <= n) return [t];
  let cut = n;
  const window = t.slice(0, n);
  for (let i = window.length - 1; i >= Math.ceil(n * 0.4); i--) {
    if (/[、，,／/\-·\s]/.test(window[i])) {
      cut = i + 1;
      break;
    }
  }
  const a = t.slice(0, cut).trim();
  let b = t.slice(cut).trim();
  if (b.length > n) b = shortLabel(b, n);
  return b ? [a, b] : [a];
}

function appendTitledText(svg, attrs, full, maxChars) {
  const lines = wrapTwoLines(full, maxChars);
  const g = svgEl("g", {});
  const tip = svgEl("title", {});
  tip.textContent = full;
  g.appendChild(tip);
  const x = attrs.x;
  const y = Number(attrs.y);
  const tAttrs = { ...attrs };
  delete tAttrs.y;
  const t = svgEl("text", tAttrs);
  if (lines.length === 1) {
    t.setAttribute("y", String(y));
    t.textContent = lines[0];
  } else {
    const lh = 13;
    const top = y - lh / 2;
    lines.forEach((line, i) => {
      const ts = svgEl("tspan", { x: String(x), y: String(top + i * lh) });
      ts.textContent = line;
      t.appendChild(ts);
    });
  }
  g.appendChild(t);
  svg.appendChild(g);
  return t;
}

function appendIpcLabel(svg, attrs, code, maxChars) {
  const zh = ipcZhTitle(code);
  const full = ipcAxisLabel(code);
  const n = Math.max(2, maxChars);
  const g = svgEl("g", {});
  const tip = svgEl("title", {});
  tip.textContent = full;
  g.appendChild(tip);
  const x = attrs.x;
  const y = Number(attrs.y);
  const tAttrs = { ...attrs };
  delete tAttrs.y;
  const t = svgEl("text", tAttrs);
  if (!zh) {
    t.setAttribute("y", String(y));
    t.textContent = code;
  } else {
    const lh = 13;
    const top = y - lh / 2;
    const l1 = svgEl("tspan", { x: String(x), y: String(top) });
    l1.textContent = code;
    t.appendChild(l1);
    const l2 = svgEl("tspan", { x: String(x), y: String(top + lh) });
    l2.textContent = zh.length <= n ? zh : shortLabel(zh, n);
    t.appendChild(l2);
  }
  g.appendChild(t);
  svg.appendChild(g);
  return t;
}

function appendAxisTitles(svg, xLabel, yLabel, x0, y0, x1, y1) {
  const ax = svgEl("text", {
    x: (x0 + x1) / 2,
    y: 20,
    "text-anchor": "middle",
    class: "matrix-head",
  });
  ax.textContent = xLabel;
  svg.appendChild(ax);
  const cx = 16;
  const cy = (y0 + y1) / 2;
  const ay = svgEl("text", {
    x: cx,
    y: cy,
    "text-anchor": "middle",
    class: "matrix-head",
    transform: `rotate(-90 ${cx} ${cy})`,
  });
  ay.textContent = yLabel;
  svg.appendChild(ay);
}

function appendDashGrid(svg, x0, y0, x1, y1, nCols, nRows) {
  appendPlotPaper(svg, x0, y0, x1, y1, { stroke: "var(--muted)", strokeWidth: "1.35" });
  const cw = (x1 - x0) / Math.max(nCols, 1);
  const ch = (y1 - y0) / Math.max(nRows, 1);
  const dash = {
    stroke: "var(--muted)",
    "stroke-width": "1.2",
    "stroke-dasharray": "5 4",
    opacity: "0.72",
  };
  for (let j = 1; j < nCols; j++) {
    const x = x0 + j * cw;
    svg.appendChild(svgEl("line", { x1: x, y1: y0, x2: x, y2: y1, ...dash }));
  }
  for (let i = 1; i < nRows; i++) {
    const y = y0 + i * ch;
    svg.appendChild(svgEl("line", { x1: x0, y1: y, x2: x1, y2: y, ...dash }));
  }
}

function openMatrixCell(row, col, items) {
  matrixDrill = { row, col, items };
  resetCam();
  render();
  showMatrixCell(row, col, items);
}

function renderHeatmap(svg, rows, cols, cell, axisY, axisX) {
  const max = Math.max(...Object.values(cell).map((v) => v.length), 1);
  const x0 = 178;
  const y0 = 98;
  const x1 = 936;
  const y1 = 500;
  const cw = Math.max(36, (x1 - x0) / Math.max(cols.length, 1));
  const ch = Math.max(26, (y1 - y0) / Math.max(rows.length, 1));
  const colChars = axisChars(cw - 8);
  const rowChars = axisChars(x0 - 36);
  appendAxisTitles(svg, axisX, axisY, x0, y0, x1, y1);
  appendPlotPaper(svg, x0, y0, x1, y1, { stroke: false });

  rows.forEach((r, i) => {
    appendTitledText(
      svg,
      {
        x: x0 - 10,
        y: y0 + i * ch + ch / 2,
        "text-anchor": "end",
        class: "matrix-axis",
      },
      r,
      rowChars
    );
    cols.forEach((c, j) => {
      if (i === 0) {
        appendIpcLabel(
          svg,
          {
            x: x0 + j * cw + cw / 2,
            y: y0 - 28,
            "text-anchor": "middle",
            class: "matrix-col",
          },
          c,
          colChars
        );
      }
      const items = cell[r + "||" + c] || [];
      const n = items.length;
      const allFb = n > 0 && items.every((p) => p.te_source === "fallback");
      const gap = Math.min(6, Math.max(2, Math.floor(Math.min(cw, ch) / 8)));
      const rect = svgEl("rect", {
        x: x0 + j * cw + gap,
        y: y0 + i * ch + gap,
        width: Math.max(cw - gap * 2, 10),
        height: Math.max(ch - gap * 2, 10),
        rx: String(Math.min(6, cw / 5, ch / 5)),
        fill: n ? (allFb ? "#8b919a" : "#5b92d9") : "var(--plot-cell)",
        opacity: n ? String(0.28 + (n / max) * 0.62) : "0.88",
        stroke: "var(--line)",
        "stroke-width": "1",
      });
      if (n) {
        rect.style.cursor = "pointer";
        rect.addEventListener("click", () => openMatrixCell(r, c, items));
      }
      svg.appendChild(rect);
      if (n && ch >= 22 && cw >= 28) {
        const num = svgEl("text", {
          x: x0 + j * cw + cw / 2,
          y: y0 + i * ch + ch / 2 + 4,
          "text-anchor": "middle",
          class: n / max > 0.55 ? "matrix-count hot" : "matrix-count",
        });
        num.textContent = String(n);
        num.style.pointerEvents = "none";
        svg.appendChild(num);
      }
    });
  });
}

function renderMatrixBubbles(svg, drill) {
  const { byRow, byCol, cell, labeled } = teCells(drill.items || []);
  const skip = (drill.items || []).length - labeled;
  const lumpR = lumpKeys(byRow, MATRIX_TOP_N);
  const lumpC = lumpKeys(byCol, MATRIX_TOP_N);
  const mapped = remapCells(cell, lumpR.map, lumpC.map);
  $("legend").innerHTML =
    `<span>点=手段 × 功效</span>` +
    `<span>低频并入「其他」</span>` +
    (lumpR.extra || lumpC.extra
      ? `<span>其余 ${lumpR.extra + lumpC.extra} 个标签计入「其他」</span>`
      : "") +
    (skip ? `<span>未入 ${skip} 篇</span>` : "") +
    filterLegend();

  const back = svgEl("text", { x: 36, y: 20, class: "matrix-head" });
  back.textContent = "← 返回";
  back.style.cursor = "pointer";
  back.addEventListener("click", () => {
    matrixDrill = null;
    selected = "";
    resetCam();
    render();
  });
  svg.appendChild(back);

  if (!lumpR.keys.length || !lumpC.keys.length) {
    const empty = svgEl("text", { x: 48, y: 72, class: "matrix-head" });
    empty.textContent = `${drill.row} × ${drill.col} 还没有手段×功效标签。`;
    svg.appendChild(empty);
    return;
  }

  const rows = lumpR.keys;
  const cols = lumpC.keys;
  const x0 = 178;
  const y0 = 88;
  const x1 = 900;
  const y1 = 500;
  const cw = (x1 - x0) / Math.max(cols.length, 1);
  const ch = (y1 - y0) / Math.max(rows.length, 1);
  const colChars = axisChars(cw - 8);
  const rowChars = axisChars(x0 - 36);
  appendAxisTitles(svg, "技术功效", "技术手段", x0, y0, x1, y1);

  rows.forEach((r, i) => {
    appendTitledText(
      svg,
      {
        x: x0 - 10,
        y: y0 + i * ch + ch / 2,
        "text-anchor": "end",
        class: "matrix-axis",
      },
      r,
      rowChars
    );
  });
  cols.forEach((c, j) => {
    appendTitledText(
      svg,
      {
        x: x0 + j * cw + cw / 2,
        y: y0 - 22,
        "text-anchor": "middle",
        class: "matrix-col",
      },
      c,
      colChars
    );
  });
  appendDashGrid(svg, x0, y0, x1, y1, cols.length, rows.length);

  const nodes = [];
  rows.forEach((r, i) => {
    cols.forEach((c, j) => {
      const items = mapped[r + "||" + c] || [];
      if (!items.length) return;
      const allFb = items.every((p) => p.te_source === "fallback");
      nodes.push({
        row: r,
        col: c,
        items,
        n: items.length,
        r: 11 + Math.min(items.length, 8) * 1.6,
        x: x0 + j * cw + cw / 2,
        y: y0 + i * ch + ch / 2,
        fb: allFb,
      });
    });
  });
  const maxN = Math.max(...nodes.map((n) => n.n), 1);
  packBubbles(nodes, x0 + 18, y0 + 18, x1 - 18, y1 - 18, 8);
  nodes.forEach((n) => {
    const c = svgEl("circle", {
      cx: n.x,
      cy: n.y,
      r: n.r,
      fill: n.fb ? "#8b919a" : "#5b92d9",
      opacity: String(0.35 + (n.n / maxN) * 0.55),
      stroke: "#fff",
      "stroke-width": "2",
    });
    c.style.cursor = "pointer";
    c.addEventListener("click", () =>
      showMatrixCell(n.row, n.col, n.items)
    );
    const tip = svgEl("title", {});
    tip.textContent = `${n.row} × ${n.col} · ${n.n} 篇`;
    c.appendChild(tip);
    svg.appendChild(c);
    const num = svgEl("text", {
      x: n.x,
      y: n.y + 4,
      "text-anchor": "middle",
      class: n.n / maxN > 0.55 ? "matrix-count hot" : "matrix-count",
    });
    num.textContent = String(n.n);
    num.style.pointerEvents = "none";
    svg.appendChild(num);
  });
}

function renderMatrix() {
  const svg = clearSvg();
  const patents = viewPatents();
  if (matrixDrill) {
    renderMatrixBubbles(svg, matrixDrill);
    return;
  }

  const scoped = !!domainFilter;
  const built = scoped ? ipcCells(patents) : ipcDomainCells(patents);
  const lumpR = lumpKeys(built.byRow, MATRIX_MAX_R);
  const lumpC = lumpKeys(built.byCol, MATRIX_MAX_C);
  const cell = remapCells(built.cell, lumpR.map, lumpC.map);
  const fallbackN = patents.filter((p) => p.te_source === "fallback").length;
  $("legend").innerHTML =
    (scoped
      ? `<span>行=本领域 · 列=IPC 小类</span>`
      : `<span>行=领域 · 列=IPC 小类</span>`) +
    `<span>点格下钻手段×功效</span>` +
    (fallbackN ? `<span>${fallbackN} 篇功效为占位</span>` : "") +
    (lumpR.extra || lumpC.extra
      ? `<span>其余 ${lumpR.extra + lumpC.extra} 个轴标签计入「其他」</span>`
      : "") +
    filterLegend();

  if (!lumpR.keys.length) {
    const empty = svgEl("text", { x: 48, y: 64, class: "matrix-head" });
    empty.textContent = domainFilter ? "该领域还没有能摊开的 IPC。" : "还没有能摊开的 IPC / 领域。";
    svg.appendChild(empty);
    return;
  }

  renderHeatmap(
    svg,
    lumpR.keys,
    lumpC.keys,
    cell,
    scoped ? "本领域" : "领域",
    "IPC 小类"
  );
}

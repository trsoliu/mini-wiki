/* 气泡/引证共用布局与短标签 */
function scaleAxis(v, vmin, vmax, a, b) {
  if (vmax <= vmin) return (a + b) / 2;
  return a + ((v - vmin) / (vmax - vmin)) * (b - a);
}

function packBubbles(nodes, x0, y0, x1, y1, gap = 16) {
  for (let iter = 0; iter < 90; iter++) {
    let moved = false;
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const minD = a.r + b.r + gap;
        const d = Math.hypot(dx, dy);
        let ux;
        let uy;
        if (d < 1e-6) {
          const ang = (i * 13 + j * 7) * 0.7;
          ux = Math.cos(ang);
          uy = Math.sin(ang);
        } else {
          ux = dx / d;
          uy = dy / d;
        }
        if (d >= minD) continue;
        const push = (minD - (d || 0)) / 2;
        a.x -= ux * push;
        a.y -= uy * push;
        b.x += ux * push;
        b.y += uy * push;
        moved = true;
      }
    }
    nodes.forEach((n) => {
      n.x = Math.max(x0 + n.r, Math.min(x1 - n.r, n.x));
      n.y = Math.max(y0 + n.r, Math.min(y1 - n.r, n.y));
    });
    if (!moved) break;
  }
}

function fitNodesToBox(nodes, x0, y0, x1, y1) {
  if (!nodes.length) return;
  const xs = nodes.map((n) => n.x);
  const ys = nodes.map((n) => n.y);
  const minx = Math.min(...xs);
  const maxx = Math.max(...xs);
  const miny = Math.min(...ys);
  const maxy = Math.max(...ys);
  const spanX = Math.max(maxx - minx, 8);
  const spanY = Math.max(maxy - miny, 8);
  const s = Math.min((x1 - x0) / spanX, (y1 - y0) / spanY);
  const cx = (minx + maxx) / 2;
  const cy = (miny + maxy) / 2;
  const mx = (x0 + x1) / 2;
  const my = (y0 + y1) / 2;
  nodes.forEach((n) => {
    n.x = mx + (n.x - cx) * s;
    n.y = my + (n.y - cy) * s;
  });
}

function median(values) {
  const s = values.filter((v) => typeof v === "number" && Number.isFinite(v)).sort((a, b) => a - b);
  if (!s.length) return 0;
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function uniqueCount(rows, key) {
  return new Set(rows.map((r) => r[key])).size;
}

function patentYear(p) {
  const d = p.filing_date || p.publication_date || "";
  const y = parseInt(String(d).slice(0, 4), 10);
  return Number.isFinite(y) && y > 1900 ? y : 0;
}

function medianOr(values, skipEmpty) {
  const s = skipEmpty ? values.filter((v) => v) : values;
  return median(s.length >= 2 ? s : values);
}

function patentLinks(p) {
  const ids = new Set([...(p.cited_pubs || []), ...(p.related_pubs || [])]);
  return ids.size + (p.nearest || []).length;
}

function pickBubbleAxes(rows) {
  const xPref = ["n", "year", "ipcN"];
  const yPref = ["links", "ipcN", "terms", "year"];
  const x = xPref.find((k) => uniqueCount(rows, k) > 1) || "n";
  const y = yPref.find((k) => k !== x && uniqueCount(rows, k) > 1) || (x === "links" ? "year" : "links");
  const labels = {
    n: { axis: "库内件数", high: "件数多", low: "件数少" },
    year: { axis: "最晚公开年", high: "较新", low: "较早" },
    links: { axis: "文内引证+关联", high: "关联多", low: "关联少" },
    ipcN: { axis: "IPC 种类", high: "门类多", low: "门类少" },
    terms: { axis: "术语条数", high: "术语多", low: "术语少" },
  };
  return { x, y, xL: labels[x], yL: labels[y] };
}

function shortAssignee(name) {
  return String(name || "")
    .replace(/股份有限公司|有限责任公司|有限公司|集团有限公司/g, "")
    .replace(/（.*?）|\(.*?\)/g, "")
    .trim()
    .slice(0, 12) || "未标";
}

function placeGutterLabels(nodes, isLeft, leftX, rightX, y0, y1) {
  const place = (arr, x, anchor) => {
    arr.sort((a, b) => a.y - b.y || a.x - b.x);
    const top = y0 + 18;
    const bot = y1 - 10;
    arr.forEach((n, i) => {
      n.lx = x;
      n.anchor = anchor;
      n.ly =
        arr.length === 1
          ? (top + bot) / 2
          : top + ((bot - top) * i) / Math.max(arr.length - 1, 1);
    });
  };
  place(nodes.filter(isLeft), leftX, "end");
  place(
    nodes.filter((n) => !isLeft(n)),
    rightX,
    "start"
  );
}

function shortLabel(s, n) {
  const t = String(s || "");
  return t.length > n ? t.slice(0, n - 1) + "…" : t;
}

function cleanTeLabel(s) {
  return String(s || "")
    .replace(/\[\[.*?\]\]/g, "")
    .replace(/\*\*|__/g, "")
    .replace(/`+/g, "")
    .replace(/^(?:[-*+]|\d+[.)、]|#{1,6})\s*/, "")
    .replace(/\s+/g, " ")
    .replace(/^[-—·\s]+|[-—·\s]+$/g, "")
    .trim();
}

function tePairs(p) {
  return (p.means_effects || []).filter((me) => me && me.mean && me.effect);
}

function ensurePaperDefs(svg) {
  let defs = svg.querySelector("defs#paper-defs");
  if (defs) return defs;
  defs = svgEl("defs", { id: "paper-defs" });
  const pat = svgEl("pattern", {
    id: "paper-dots",
    width: "12",
    height: "12",
    patternUnits: "userSpaceOnUse",
  });
  pat.appendChild(
    svgEl("circle", {
      cx: "1.15",
      cy: "1.15",
      r: "0.8",
      fill: "var(--plot-dot)",
    })
  );
  defs.appendChild(pat);
  svg.appendChild(defs);
  return defs;
}

function appendPlotPaper(svg, x0, y0, x1, y1, extra) {
  extra = extra || {};
  ensurePaperDefs(svg);
  const g = svgEl("g", { class: "plot-paper" });
  g.style.pointerEvents = "none";
  const box = {
    x: x0,
    y: y0,
    width: x1 - x0,
    height: y1 - y0,
  };
  if (extra.rx) box.rx = extra.rx;
  g.appendChild(svgEl("rect", { ...box, fill: extra.fill || "var(--plot)" }));
  g.appendChild(svgEl("rect", { ...box, fill: "url(#paper-dots)" }));
  if (extra.stroke !== false) {
    g.appendChild(
      svgEl("rect", {
        ...box,
        fill: "none",
        stroke: extra.stroke || "var(--plot-edge)",
        "stroke-width": extra.strokeWidth || "1.2",
      })
    );
  }
  svg.appendChild(g);
  return g;
}

function appendFieldRings(svg, x0, y0, x1, y1) {
  const defs = ensurePaperDefs(svg);
  let clip = defs.querySelector("#field-rings-clip");
  if (clip) clip.remove();
  clip = svgEl("clipPath", { id: "field-rings-clip" });
  clip.appendChild(svgEl("rect", { x: x0, y: y0, width: x1 - x0, height: y1 - y0 }));
  defs.appendChild(clip);
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;
  const maxR = Math.hypot(x1 - x0, y1 - y0) / 2;
  const g = svgEl("g", { class: "field-rings", "clip-path": "url(#field-rings-clip)" });
  g.style.pointerEvents = "none";
  for (let i = 1; i <= 4; i++) {
    g.appendChild(
      svgEl("circle", {
        cx,
        cy,
        r: (maxR * i) / 4.15,
        fill: "none",
        stroke: "var(--plot-ring)",
        "stroke-width": "1",
        opacity: String(0.72 - i * 0.1),
      })
    );
  }
  svg.appendChild(g);
  return g;
}

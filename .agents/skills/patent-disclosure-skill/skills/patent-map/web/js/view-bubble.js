/* 申请人四象限 */
function renderBubble() {
  const svg = clearSvg();
  const patents = viewPatents();
  const x0 = 196;
  const y0 = 42;
  const x1 = 764;
  const y1 = 448;
  const by = {};
  patents.forEach((p) => {
    const a = (p.assignees && p.assignees[0]) || "未标申请人";
    const row = (by[a] ||= {
      name: a,
      n: 0,
      ipc: new Set(),
      terms: new Set(),
      links: 0,
      year: 0,
      sample: p,
    });
    row.n += 1;
    (p.ipc_codes || []).forEach((c) => row.ipc.add(ipcPrefix({ ipc_codes: [c], ipc: c })));
    if (!p.ipc_codes || !p.ipc_codes.length) row.ipc.add(ipcPrefix(p));
    (p.terms || []).forEach((t) => row.terms.add(t));
    row.links += patentLinks(p);
    row.year = Math.max(row.year, patentYear(p));
  });
  const rows = Object.values(by).map((r) => ({
    ...r,
    ipcN: r.ipc.size,
    terms: r.terms.size,
  }));
  if (!rows.length) {
    $("legend").innerHTML = filterLegend();
    const empty = svgEl("text", { x: 48, y: 64, class: "axis-name" });
    empty.textContent = domainFilter ? "该领域还没有已读专利。" : "还没有已读专利。";
    svg.appendChild(empty);
    return;
  }
  const axes = pickBubbleAxes(rows);
  const xv = (r) => r[axes.x];
  const yv = (r) => r[axes.y];
  const minX = Math.min(...rows.map(xv));
  const maxX = Math.max(...rows.map(xv));
  const minY = Math.min(...rows.map(yv));
  const maxY = Math.max(...rows.map(yv));
  const medX = medianOr(rows.map(xv), axes.x === "year");
  const medY = median(rows.map(yv));
  const maxN = Math.max(...rows.map((r) => r.n), 1);
  const px = (v) => scaleAxis(v, minX, maxX, x0 + 36, x1 - 36);
  const py = (v) => scaleAxis(v, minY, maxY, y1 - 36, y0 + 36);
  const midX = px(medX);
  const midY = py(medY);

  appendPlotPaper(svg, x0, y0, x1, y1, { stroke: false });
  const qfills = [
    [x0, y0, midX - x0, midY - y0, "rgba(91,146,217,0.2)"],
    [midX, y0, x1 - midX, midY - y0, "rgba(90,168,118,0.2)"],
    [x0, midY, midX - x0, y1 - midY, "rgba(196,138,160,0.2)"],
    [midX, midY, x1 - midX, y1 - midY, "rgba(208,138,106,0.2)"],
  ];
  qfills.forEach(([x, y, w, h, fill]) => {
    if (w > 0 && h > 0) svg.appendChild(svgEl("rect", { x, y, width: w, height: h, fill, stroke: "none" }));
  });
  svg.appendChild(svgEl("rect", {
    x: x0, y: y0, width: x1 - x0, height: y1 - y0,
    fill: "none", stroke: "#3a4254", "stroke-width": "1.2",
  }));
  [
    { x1: midX, y1: y0, x2: midX, y2: y1 },
    { x1: x0, y1: midY, x2: x1, y2: midY },
  ].forEach((ln) => {
    svg.appendChild(svgEl("line", { ...ln, stroke: "var(--elev)", "stroke-width": "5", opacity: "0.9" }));
    svg.appendChild(svgEl("line", {
      ...ln,
      stroke: "var(--text)",
      "stroke-width": "1.6",
      "stroke-dasharray": "7 5",
      opacity: "0.72",
    }));
  });

  const qLabels = [
    { x: x0 + 10, y: y0 + 18, anchor: "start", t: `${axes.xL.low} · ${axes.yL.high}` },
    { x: x1 - 10, y: y0 + 18, anchor: "end", t: `${axes.xL.high} · ${axes.yL.high}` },
    { x: x0 + 10, y: y1 - 12, anchor: "start", t: `${axes.xL.low} · ${axes.yL.low}` },
    { x: x1 - 10, y: y1 - 12, anchor: "end", t: `${axes.xL.high} · ${axes.yL.low}` },
  ];
  qLabels.forEach((q) => {
    const el = svgEl("text", { x: q.x, y: q.y, "text-anchor": q.anchor, class: "quad-tag" });
    el.textContent = q.t;
    svg.appendChild(el);
  });
  const ax = svgEl("text", { x: (x0 + x1) / 2, y: 500, "text-anchor": "middle", class: "axis-name" });
  ax.textContent = axes.xL.axis + " →";
  svg.appendChild(ax);
  const ay = svgEl("text", { x: 12, y: 22, class: "axis-name" });
  ay.textContent = "↑ " + axes.yL.axis;
  svg.appendChild(ay);

  const nodes = rows.map((r, i) => {
    const ang = i * 2.399963;
    return {
      ...r,
      idx: i + 1,
      r: 12 + (r.n / maxN) * 10,
      x: px(xv(r)) + Math.cos(ang) * 5,
      y: py(yv(r)) + Math.sin(ang) * 5,
    };
  });
  packBubbles(nodes, x0 + 18, y0 + 26, x1 - 18, y1 - 20, 14);
  const splitX = (x0 + x1) / 2;
  placeGutterLabels(nodes, (n) => n.x < splitX, 184, 776, y0, y1);

  const qColor = (n) => {
    const right = n.x >= midX;
    const up = n.y <= midY;
    if (right && up) return "#5b92d9";
    if (!right && up) return "#5aa876";
    if (right && !up) return "#d08a6a";
    return "#c48aa0";
  };
  nodes.forEach((n) => {
    const edgeX = n.anchor === "end" ? n.x - n.r - 2 : n.x + n.r + 2;
    svg.appendChild(
      svgEl("line", {
        x1: n.lx,
        y1: n.ly - 3,
        x2: edgeX,
        y2: n.y,
        stroke: "#6a7384",
        "stroke-width": "1",
        opacity: "0.55",
      })
    );
  });
  nodes.forEach((n) => {
    const c = svgEl("circle", {
      cx: n.x,
      cy: n.y,
      r: n.r,
      fill: qColor(n),
      stroke: "#fff",
      "stroke-width": "2",
    });
    c.style.cursor = "pointer";
    c.addEventListener("click", () => showDetail(n.sample));
    svg.appendChild(c);
    const title = svgEl("title", {});
    title.textContent = `${n.name} · ${axes.xL.axis} ${xv(n)} · ${axes.yL.axis} ${yv(n)}`;
    c.appendChild(title);
    const num = svgEl("text", {
      x: n.x,
      y: n.y + 4,
      "text-anchor": "middle",
      class: "bubble-idx",
    });
    num.textContent = String(n.idx);
    num.style.pointerEvents = "none";
    svg.appendChild(num);
    const t = svgEl("text", {
      x: n.anchor === "end" ? n.lx - 2 : n.lx + 2,
      y: n.ly,
      "text-anchor": n.anchor,
      class: "bubble-label",
    });
    t.textContent = `${n.idx} ${shortAssignee(n.name)}`;
    t.style.cursor = "pointer";
    t.addEventListener("click", () => showDetail(n.sample));
    svg.appendChild(t);
  });
  $("legend").innerHTML =
    `<span>十字=中位数</span>` +
    `<span>横 ${axes.xL.axis}</span>` +
    `<span>纵 ${axes.yL.axis}</span>` +
    `<span>编号对应两侧名单</span>` +
    filterLegend();
}

/* 同族引证网络 */
function renderCitation() {
  const svg = clearSvg();
  const patents = viewPatents();
  const x0 = 72;
  const y0 = 48;
  const x1 = 888;
  const y1 = 456;
  $("legend").innerHTML =
    (hasSemantic() ? "<span>实线引证 · 虚线语义近邻</span>" : "<span>实线=两边都已读的引证</span>") +
    filterLegend();
  if (!patents.length) {
    const empty = svgEl("text", { x: 48, y: 64, class: "cite-label" });
    empty.textContent = domainFilter ? "该领域还没有已读专利。" : "还没有已读专利。";
    svg.appendChild(empty);
    return;
  }
  const nodes = new Map();
  patents.forEach((p, i) => {
    const xy = hasSemantic()
      ? mapPoint(p, MAP_W, MAP_H, 100)
      : { x: 140 + (i % 5) * 160, y: 100 + Math.floor(i / 5) * 140 };
    nodes.set(p.pub, { pub: p.pub, x: xy.x, y: xy.y, r: 38, p });
  });
  const arr = [...nodes.values()];
  packBubbles(arr, x0, y0, x1, y1, 12);
  fitNodesToBox(arr, x0, y0, x1, y1);
  packBubbles(arr, x0, y0, x1, y1, 10);

  appendPlotPaper(svg, x0, y0, x1, y1);
  appendFieldRings(svg, x0, y0, x1, y1);

  const citedEdge = new Set();
  patents.forEach((p) => {
    const a = nodes.get(p.pub);
    (p.cited_pubs || []).forEach((c) => {
      const b = nodes.get(c);
      if (!a || !b) return;
      citedEdge.add([p.pub, c].sort().join("|"));
      svg.appendChild(
        svgEl("line", {
          x1: a.x,
          y1: a.y,
          x2: b.x,
          y2: b.y,
          stroke: "#7b8494",
          "stroke-width": "1.4",
          opacity: "0.62",
        })
      );
    });
    (p.nearest || []).slice(0, 2).forEach((n) => {
      const b = nodes.get(n.pub);
      if (!a || !b || a.pub === b.pub) return;
      if (citedEdge.has([a.pub, b.pub].sort().join("|"))) return;
      svg.appendChild(
        svgEl("line", {
          x1: a.x,
          y1: a.y,
          x2: b.x,
          y2: b.y,
          stroke: "#5b92d9",
          "stroke-width": "1.2",
          "stroke-dasharray": "5 5",
          opacity: "0.48",
        })
      );
    });
  });

  arr.forEach((n) => {
    const c = svgEl("circle", {
      cx: n.x,
      cy: n.y,
      r: 13,
      fill: domainColor(n.p.domain),
      stroke: "#fff",
      "stroke-width": "2.2",
    });
    c.style.cursor = "pointer";
    c.addEventListener("click", () => showDetail(n.p));
    const tip = svgEl("title", {});
    tip.textContent = n.pub;
    c.appendChild(tip);
    svg.appendChild(c);
    const t = svgEl("text", {
      x: n.x,
      y: n.y + 28,
      "text-anchor": "middle",
      class: "cite-label",
    });
    t.textContent = n.pub;
    t.style.cursor = "pointer";
    t.addEventListener("click", () => showDetail(n.p));
    svg.appendChild(t);
  });
}

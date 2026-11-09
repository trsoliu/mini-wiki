/* 统计仪表盘 */
function renderDashboard() {
  const svg = clearSvg();
  const patents = viewPatents();
  if (!patents.length) {
    $("legend").innerHTML = filterLegend();
    const empty = svgEl("text", { x: 48, y: 64, class: "dash-title" });
    empty.textContent = domainFilter ? "该领域还没有已读专利。" : "还没有已读专利。";
    svg.appendChild(empty);
    return;
  }
  const years = {};
  const asg = {};
  const byYear = {};
  patents.forEach((p) => {
    const y = yearOf(p);
    const a = firstAssignee(p);
    years[y] = (years[y] || 0) + 1;
    (byYear[y] ||= []).push(p);
    asg[a] = (asg[a] || 0) + 1;
  });
  const pal = assigneePalette(asg);
  const byBucket = {};
  patents.forEach((p) => {
    const b = pal.bucket(firstAssignee(p));
    (byBucket[b] ||= []).push(p);
  });
  const numYears = Object.keys(years)
    .filter((y) => y !== "未标年")
    .sort();
  const ykeys = years["未标年"] ? numYears.concat(["未标年"]) : numYears;
  const maxY = Math.max(...Object.values(years), 1);
  const pieRows = pal.names.map((name) => [name, (byBucket[name] || []).length]).filter((r) => r[1]);
  const pieTotal = pieRows.reduce((s, r) => s + r[1], 0) || 1;
  $("legend").innerHTML =
    pal.names
      .map((name) => {
        const n = (byBucket[name] || []).length;
        const label = name === ASG_OTHER ? `${ASG_OTHER}（${pal.rest.length} 家）` : shortAssignee(name);
        return `<span><i class="swatch" style="background:${pal.colorOf[name]}"></i>${label} ${n}</span>`;
      })
      .join("") + filterLegend();

  const x0 = 56;
  const y0 = 64;
  const x1 = 500;
  const y1 = 418;
  const visW = x1 - x0;
  const n = Math.max(ykeys.length, 1);
  const slot = Math.max(44, visW / n);
  const contentW = slot * n;
  const needScroll = contentW > visW + 0.5;
  dashScroll.x0 = x0;
  dashScroll.x1 = x1;
  dashScroll.y0 = y0 - 28;
  dashScroll.y1 = 478;
  dashScroll.vis = visW;
  dashScroll.content = contentW;
  dashScroll.max = Math.max(0, contentW - visW);
  dashScroll.active = needScroll;
  dashScroll.x = Math.max(0, Math.min(dashScroll.max, dashScroll.x));

  const titleL = svgEl("text", { x: x0, y: 28, class: "dash-title" });
  titleL.textContent = "按年件数（色块=申请人）";
  svg.appendChild(titleL);
  const xCap = svgEl("text", { x: x0, y: 44, class: "dash-tick" });
  xCap.textContent = needScroll ? "申请日优先，否则公开日 · 条多时可左右拖动" : "年份：申请日优先，否则公开日";
  svg.appendChild(xCap);
  appendPlotPaper(svg, x0, y0, x1, y1, { stroke: false });
  svg.appendChild(
    svgEl("line", { x1: x0, y1: y1, x2: x1, y2: y1, stroke: "var(--line)", "stroke-width": "1.2" })
  );
  svg.appendChild(
    svgEl("line", { x1: x0, y1: y0, x2: x0, y2: y1, stroke: "var(--line)", "stroke-width": "1.2" })
  );
  const labeled = new Set([0, Math.round(maxY / 2), maxY]);
  [0, 0.25, 0.5, 0.75, 1]
    .map((t) => Math.round(maxY * t))
    .filter((tick, i, arr) => arr.indexOf(tick) === i)
    .forEach((tick) => {
      const yy = y1 - (tick / Math.max(maxY, 1)) * (y1 - y0 - 8);
      const strong = labeled.has(tick);
      svg.appendChild(
        svgEl("line", {
          x1: x0,
          y1: yy,
          x2: x1,
          y2: yy,
          stroke: "var(--line)",
          "stroke-width": strong ? "1" : "0.8",
          opacity: strong ? "0.7" : "0.32",
        })
      );
      if (strong) {
        const lab = svgEl("text", { x: x0 - 8, y: yy + 4, "text-anchor": "end", class: "dash-tick" });
        lab.textContent = String(tick);
        svg.appendChild(lab);
      }
    });

  const defs = svgEl("defs", {});
  const clip = svgEl("clipPath", { id: "dash-clip" });
  clip.appendChild(
    svgEl("rect", {
      x: x0,
      y: y0 - 28,
      width: visW,
      height: y1 - y0 + 56,
    })
  );
  defs.appendChild(clip);
  svg.appendChild(defs);

  const clipped = svgEl("g", { "clip-path": "url(#dash-clip)" });
  const bars = svgEl("g", { id: "dash-bars" });
  const bw = Math.max(18, Math.min(40, slot * 0.55));
  ykeys.forEach((y, i) => {
    const items = byYear[y] || [];
    const count = items.length;
    const fullH = count ? Math.max(8, (count / maxY) * (y1 - y0 - 16)) : 0;
    const cx = x0 + slot * i + slot / 2;
    const grouped = {};
    items.forEach((p) => {
      const b = pal.bucket(firstAssignee(p));
      (grouped[b] ||= []).push(p);
    });
    let yb = y1;
    pal.names.forEach((name) => {
      const part = grouped[name];
      if (!part || !part.length) return;
      const h = fullH * (part.length / count);
      yb -= h;
      const seg = svgEl("rect", {
        x: cx - bw / 2,
        y: yb,
        width: bw,
        height: Math.max(h, 1.2),
        fill: pal.colorOf[name],
      });
      seg.style.cursor = "pointer";
      const tip = svgEl("title", {});
      tip.textContent = `${y === "未标年" ? "未标年" : y} · ${name} · ${part.length}`;
      seg.appendChild(tip);
      seg.addEventListener("click", () =>
        showDashList(
          `${y === "未标年" ? "未标年" : y + " 年"} · ${name === ASG_OTHER ? ASG_OTHER : shortAssignee(name)}`,
          "该年该申请人",
          part
        )
      );
      bars.appendChild(seg);
    });
    if (count) {
      const num = svgEl("text", { x: cx, y: y1 - fullH - 8, "text-anchor": "middle", class: "dash-count" });
      num.textContent = String(count);
      num.style.pointerEvents = "none";
      bars.appendChild(num);
    }
    const lab = svgEl("text", { x: cx, y: y1 + 20, "text-anchor": "middle", class: "dash-tick" });
    lab.textContent = y === "未标年" ? "未标年" : y;
    lab.style.cursor = "pointer";
    lab.addEventListener("click", () =>
      showDashList(y === "未标年" ? "未标年" : `${y} 年`, "申请日优先，否则公开日", items)
    );
    bars.appendChild(lab);
  });
  clipped.appendChild(bars);
  svg.appendChild(clipped);

  if (needScroll) {
    const trackY = 456;
    svg.appendChild(
      svgEl("rect", {
        id: "dash-track",
        x: x0,
        y: trackY,
        width: visW,
        height: 10,
        rx: 5,
        fill: "var(--fill2)",
        stroke: "var(--line)",
        "stroke-width": "1",
        cursor: "pointer",
      })
    );
    const thumb = svgEl("rect", {
      id: "dash-thumb",
      x: x0,
      y: trackY + 1,
      width: 28,
      height: 8,
      rx: 4,
      fill: "var(--muted)",
    });
    thumb.style.cursor = "pointer";
    svg.appendChild(thumb);
  }
  applyDashScroll();

  const pcx = 720;
  const pcy = 250;
  const r1 = 112;
  const r0 = 58;
  const titleR = svgEl("text", { x: 548, y: 28, class: "dash-title" });
  titleR.textContent = "申请人占比";
  svg.appendChild(titleR);
  appendPlotPaper(svg, pcx - r1 - 18, pcy - r1 - 18, pcx + r1 + 18, pcy + r1 + 18, {
    rx: String(r1 + 18),
    stroke: false,
  });
  let ang = -Math.PI / 2;
  pieRows.forEach(([name, count]) => {
    const slice = (count / pieTotal) * Math.PI * 2;
    const a1 = ang + slice;
    const path = svgEl("path", {
      d: donutSlice(pcx, pcy, r0, r1, ang, a1),
      fill: pal.colorOf[name],
      stroke: "#fff",
      "stroke-width": "2",
    });
    path.style.cursor = "pointer";
    const tip = svgEl("title", {});
    tip.textContent = `${name} · ${count} 篇（${Math.round((count / pieTotal) * 100)}%）`;
    path.appendChild(tip);
    path.addEventListener("click", () =>
      showDashList(name === ASG_OTHER ? `${ASG_OTHER}（${pal.rest.length} 家）` : name, "第一申请人", byBucket[name] || [])
    );
    svg.appendChild(path);
    if (slice > 0.35) {
      const mid = ang + slice / 2;
      const lx = pcx + Math.cos(mid) * ((r0 + r1) / 2);
      const ly = pcy + Math.sin(mid) * ((r0 + r1) / 2);
      const pct = svgEl("text", { x: lx, y: ly + 4, "text-anchor": "middle", class: "dash-count hot" });
      pct.textContent = String(count);
      pct.style.pointerEvents = "none";
      svg.appendChild(pct);
    }
    ang = a1;
  });
  const hub = svgEl("text", { x: pcx, y: pcy - 2, "text-anchor": "middle", class: "dash-count" });
  hub.textContent = String(pieTotal);
  svg.appendChild(hub);
  const hub2 = svgEl("text", { x: pcx, y: pcy + 16, "text-anchor": "middle", class: "dash-tick" });
  hub2.textContent = "篇";
  svg.appendChild(hub2);
}

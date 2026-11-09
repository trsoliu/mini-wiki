/* 常量、共享状态、通用工具 */
const VIEWS = [
  { id: "terrain", name: "地形 / 3D沙盘" },
  { id: "bubble", name: "申请人四象限" },
  { id: "citation", name: "同族引证网络" },
  { id: "matrix", name: "技术功效矩阵" },
  { id: "dashboard", name: "统计仪表盘" },
];

const DOMAIN_COLORS = ["#80b6ff", "#7ee0a3", "#f0c36d", "#e89ab8", "#b8a4ff", "#8ad4d4", "#f3a27a", "#9ad0f5"];
const ASG_COLORS = ["#5b92d9", "#5aa876", "#d08a6a", "#8b7cc8", "#c48aa0", "#e2b15a", "#4aa3b5", "#6b8cae"];
const ASG_OTHER = "其他申请人";
const ASG_OTHER_COLOR = "#9aa3b5";
const ASG_KEEP = 7;

const MAP_W = 960;
const MAP_H = 520;
const TERRAIN_STOPS = [
  [0, [243, 242, 238]],
  [0.18, [232, 230, 223]],
  [0.36, [210, 211, 216]],
  [0.54, [168, 196, 232]],
  [0.74, [91, 146, 217]],
  [1, [45, 108, 181]],
];

let DATA = { patents: [], domains: [], ipc_titles: {}, source: "", vault: "", vault_count: 0, embedding: {} };
let view = "terrain";
let selected = "";
let selectedCluster = -1;
let domainFilter = "";
let matrixDrill = null;
let camState = { k: 1, x: 0, y: 0 };
let lastView = "";
let TERRAIN = { pts: [], clusters: [], field: null };
let detailStack = [];

const ANALYZE_VIEWS = new Set(["bubble", "citation", "matrix", "dashboard"]);
const AXIS_OTHER = "其他";

const $ = (id) => document.getElementById(id);

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function mdInline(s) {
  let t = escapeHtml(s);
  t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
  t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  t = t.replace(/__([^_]+)__/g, "<strong>$1</strong>");
  t = t.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
  return t;
}

function plainText(s, n) {
  const t = String(s ?? "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1");
  return n ? t.slice(0, n) : t;
}

function ipcPrefix(p) {
  const c = (p && p.ipc_codes && p.ipc_codes[0]) || (p && p.ipc) || "";
  const s = String(c).replace(/\s/g, "").toUpperCase();
  const m = s.match(/^([A-HY]\d{2}[A-Z])/);
  return m ? m[1] : "其他";
}

function ipcPrefixesOf(p) {
  const codes = (p.ipc_codes && p.ipc_codes.length ? p.ipc_codes : [p.ipc]).filter(Boolean);
  const out = [...new Set(codes.map((c) => ipcPrefix({ ipc_codes: [c], ipc: c })))];
  return out.length ? out : ["其他"];
}

function ipcZhTitle(code) {
  if (!code || code === AXIS_OTHER) return "";
  const t = (DATA.ipc_titles || {})[code];
  return typeof t === "string" ? t.trim() : "";
}

function ipcAxisLabel(code) {
  const zh = ipcZhTitle(code);
  return zh ? `${code} ${zh}` : code;
}

function yearOf(p) {
  const d = String(p.filing_date || p.publication_date || "").slice(0, 4);
  return /^\d{4}$/.test(d) ? d : "未标年";
}

function firstAssignee(p) {
  return (p.assignees && p.assignees[0]) || "未标申请人";
}

function assigneePalette(counts) {
  const ranked = Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "zh"));
  const lump = ranked.length > ASG_KEEP + 1;
  const keep = ranked.slice(0, lump ? ASG_KEEP : ranked.length);
  const rest = lump ? ranked.slice(ASG_KEEP) : [];
  const colorOf = {};
  keep.forEach(([name], i) => {
    colorOf[name] = ASG_COLORS[i % ASG_COLORS.length];
  });
  if (rest.length) colorOf[ASG_OTHER] = ASG_OTHER_COLOR;
  const names = keep.map((r) => r[0]).concat(rest.length ? [ASG_OTHER] : []);
  const bucket = (name) => (colorOf[name] ? name : ASG_OTHER);
  return { colorOf, bucket, names, rest };
}

function donutSlice(cx, cy, r0, r1, a0, a1) {
  const large = a1 - a0 > Math.PI ? 1 : 0;
  const p = (r, a) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  const [x0, y0] = p(r1, a0);
  const [x1, y1] = p(r1, a1);
  const [x2, y2] = p(r0, a1);
  const [x3, y3] = p(r0, a0);
  return `M ${x0} ${y0} A ${r1} ${r1} 0 ${large} 1 ${x1} ${y1} L ${x2} ${y2} A ${r0} ${r0} 0 ${large} 0 ${x3} ${y3} Z`;
}

function domainColor(name) {
  const keys = [...new Set(DATA.patents.map((p) => p.domain || "未分类"))];
  const i = Math.max(0, keys.indexOf(name || "未分类"));
  return DOMAIN_COLORS[i % DOMAIN_COLORS.length];
}

function hasSemantic() {
  return DATA.patents.some((p) => typeof p.x === "number" && typeof p.y === "number");
}

function findPub(pub) {
  return DATA.patents.find((p) => p.pub === pub);
}

function domainCatalog() {
  if (Array.isArray(DATA.domains) && DATA.domains.length) return DATA.domains;
  const map = new Map();
  DATA.patents.forEach((p) => {
    const name = p.domain || "未分类";
    const id = p.domain_id || name;
    const row = map.get(id) || { id, name, count: 0 };
    row.count += 1;
    map.set(id, row);
  });
  return [...map.values()].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, "zh"));
}

function viewPatents() {
  if (!ANALYZE_VIEWS.has(view) || !domainFilter) return DATA.patents;
  return DATA.patents.filter(
    (p) => (p.domain_id || "") === domainFilter || (p.domain || "未分类") === domainFilter
  );
}

function currentDomainName() {
  if (!domainFilter) return "";
  const hit = domainCatalog().find((d) => d.id === domainFilter || d.name === domainFilter);
  return hit ? hit.name : domainFilter;
}

function filterLegend() {
  if (!ANALYZE_VIEWS.has(view) || !domainFilter) return "";
  const n = viewPatents().length;
  return `<span>领域 ${escapeHtml(currentDomainName())} · ${n} 篇</span>`;
}

function dropOutsideFilter() {
  if (!domainFilter || view === "terrain") return;
  const pubs = new Set(viewPatents().map((p) => p.pub));
  if (selected && !pubs.has(selected)) {
    selected = "";
    selectedCluster = -1;
    detailStack = [];
  }
}


function clearSvg() {
  const svg = $("chart");
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  return svg;
}

function svgEl(name, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}

function mapPoint(p, w, h, pad) {
  const x = pad + (typeof p.x === "number" ? p.x : 0.5) * (w - 2 * pad);
  const y = pad + (typeof p.y === "number" ? p.y : 0.5) * (h - 2 * pad);
  return { x, y };
}

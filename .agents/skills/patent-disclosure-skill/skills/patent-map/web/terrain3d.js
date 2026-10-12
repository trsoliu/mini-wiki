/* 专利地图地形：Three.js 透视网格。无 WebGL / 未加载库时由视图退回 2.5D。 */
import * as THREE from "./vendor/three.module.min.js";

const MAP_W = 960;
const MAP_H = 520;
const ASPECT_Z = MAP_H / MAP_W;
const CLEAR = 0xefece6;
const STOPS = [
  [0, [243, 242, 238]],
  [0.18, [232, 230, 223]],
  [0.36, [210, 211, 216]],
  [0.54, [168, 196, 232]],
  [0.74, [91, 146, 217]],
  [1, [45, 108, 181]],
];

let canvas = null;
let renderer = null;
let scene = null;
let camera = null;
let land = null;
let cam = { yaw: 0.62, pitch: 0.58, dist: 2.35 };
let readyMesh = false;
const _ndc = new THREE.Vector3();
const _look = new THREE.Vector3(0, 0.12, 0);

function mixStops(t) {
  t = Math.max(0, Math.min(1, t));
  for (let i = 1; i < STOPS.length; i++) {
    if (t <= STOPS[i][0]) {
      const [t0, c0] = STOPS[i - 1];
      const [t1, c1] = STOPS[i];
      const u = (t - t0) / (t1 - t0 || 1);
      return c0.map((v, k) => v + (c1[k] - v) * u);
    }
  }
  return STOPS[STOPS.length - 1][1];
}

function pushLinear(arr, rgb, scale = 1) {
  const c = new THREE.Color();
  c.setRGB((rgb[0] / 255) * scale, (rgb[1] / 255) * scale, (rgb[2] / 255) * scale, THREE.SRGBColorSpace);
  arr.push(c.r, c.g, c.b);
}

function mapToWorld(x, y, z) {
  return [
    (x / MAP_W - 0.5) * 2,
    0.018 + Math.max(0, z) * 0.62,
    (y / MAP_H - 0.5) * 2 * ASPECT_Z,
  ];
}

function eyePos() {
  const { yaw, pitch, dist } = cam;
  const cp = Math.cos(pitch);
  return new THREE.Vector3(dist * cp * Math.sin(yaw), 0.12 + dist * Math.sin(pitch), dist * cp * Math.cos(yaw));
}

function updateCamera() {
  if (!camera || !canvas) return;
  const w = canvas.clientWidth || canvas.width || MAP_W;
  const h = canvas.clientHeight || canvas.height || MAP_H;
  camera.aspect = w / h;
  camera.position.copy(eyePos());
  camera.lookAt(_look);
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld();
}

function disposeObject(obj) {
  if (!obj) return;
  obj.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
    mats.forEach((m) => m && m.dispose());
  });
}

function clearLand() {
  if (!scene || !land) {
    readyMesh = false;
    return;
  }
  scene.remove(land);
  disposeObject(land);
  land = null;
  readyMesh = false;
}

function isolines(field, level) {
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
    5: [
      [3, 0],
      [1, 2],
    ],
    6: [[0, 2]],
    7: [[3, 2]],
    8: [[2, 3]],
    9: [[0, 2]],
    10: [
      [0, 1],
      [2, 3],
    ],
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
        (v[0] >= level ? 1 : 0) | (v[1] >= level ? 2 : 0) | (v[2] >= level ? 4 : 0) | (v[3] >= level ? 8 : 0);
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

function init(el) {
  if (renderer && canvas === el) return true;
  canvas = el;
  if (!canvas) return false;
  if (renderer) return true;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
  } catch (_) {
    renderer = null;
    return false;
  }
  if (!renderer.getContext()) {
    renderer.dispose();
    renderer = null;
    return false;
  }
  renderer.setClearColor(CLEAR, 1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.92;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(CLEAR);
  scene.fog = new THREE.Fog(CLEAR, 2.4, 6.8);

  camera = new THREE.PerspectiveCamera(42, MAP_W / MAP_H, 0.08, 20);

  const hemi = new THREE.HemisphereLight(0xd7e6f7, 0xc9c0b0, 0.88);
  scene.add(hemi);
  const key = new THREE.DirectionalLight(0xfff4e6, 1.35);
  key.position.set(1.15, 2.05, 0.72);
  key.castShadow = true;
  key.shadow.mapSize.set(1536, 1536);
  key.shadow.camera.near = 0.2;
  key.shadow.camera.far = 8;
  key.shadow.camera.left = -2.3;
  key.shadow.camera.right = 2.3;
  key.shadow.camera.top = 1.7;
  key.shadow.camera.bottom = -1.7;
  key.shadow.bias = -0.0007;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xb8d0ea, 0.38);
  fill.position.set(-1.4, 0.9, -0.8);
  scene.add(fill);
  const rim = new THREE.DirectionalLight(0xffffff, 0.22);
  rim.position.set(-0.2, 1.4, 1.6);
  scene.add(rim);

  const ground = new THREE.Mesh(
    new THREE.CircleGeometry(2.35, 64),
    new THREE.MeshStandardMaterial({
      color: 0xd8d2c6,
      roughness: 0.92,
      metalness: 0.02,
    })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.002;
  ground.receiveShadow = true;
  scene.add(ground);

  const plinth = new THREE.Mesh(
    new THREE.BoxGeometry(2.18, 0.055, 2.18 * ASPECT_Z + 0.1),
    new THREE.MeshStandardMaterial({ color: 0xc4beb2, roughness: 0.74, metalness: 0.04 })
  );
  plinth.position.y = -0.03;
  plinth.castShadow = true;
  plinth.receiveShadow = true;
  scene.add(plinth);

  return true;
}

function ready() {
  return !!(renderer && scene && camera && readyMesh);
}

function resize() {
  if (!canvas || !renderer) return;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const w = Math.max(1, Math.round((canvas.clientWidth || MAP_W) * dpr));
  const h = Math.max(1, Math.round((canvas.clientHeight || MAP_H) * dpr));
  if (canvas.width !== w || canvas.height !== h) renderer.setSize(w, h, false);
  updateCamera();
}

function setField(field) {
  if (!renderer || !scene || !field) {
    clearLand();
    return false;
  }
  clearLand();
  const { grid, cols, rows, cw, ch } = field;
  const nx = cols + 1;
  const nz = rows + 1;
  const pos = [];
  const col = [];
  const idx = [];

  function worldAt(c, r) {
    const x = c * cw;
    const y = r * ch;
    const z = grid[Math.max(0, Math.min(rows, r))][Math.max(0, Math.min(cols, c))];
    return mapToWorld(x, y, z);
  }

  for (let r = 0; r < nz; r++) {
    for (let c = 0; c < nx; c++) {
      const p = worldAt(c, r);
      const h = grid[Math.max(0, Math.min(rows, r))][Math.max(0, Math.min(cols, c))];
      pos.push(p[0], p[1], p[2]);
      pushLinear(col, mixStops(h));
    }
  }
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const a = r * nx + c;
      idx.push(a, a + 1, a + nx, a + 1, a + nx + 1, a + nx);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  const mesh = new THREE.Mesh(
    geo,
    new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.78,
      metalness: 0.06,
      envMapIntensity: 0.35,
    })
  );
  mesh.castShadow = true;
  mesh.receiveShadow = true;

  const skirtPos = [];
  const skirtCol = [];
  const skirtIdx = [];
  function pushSkirt(c0, r0, c1, r1) {
    const t0 = worldAt(c0, r0);
    const t1 = worldAt(c1, r1);
    const base = skirtPos.length / 3;
    skirtPos.push(t0[0], t0[1], t0[2], t1[0], t1[1], t1[2], t1[0], 0, t1[2], t0[0], 0, t0[2]);
    for (let k = 0; k < 4; k++) pushLinear(skirtCol, mixStops(0), 0.78);
    skirtIdx.push(base, base + 3, base + 2, base, base + 2, base + 1);
  }
  for (let c = 0; c < cols; c++) {
    pushSkirt(c, 0, c + 1, 0);
    pushSkirt(c + 1, rows, c, rows);
  }
  for (let r = 0; r < rows; r++) {
    pushSkirt(0, r + 1, 0, r);
    pushSkirt(cols, r, cols, r + 1);
  }
  const skirtGeo = new THREE.BufferGeometry();
  skirtGeo.setAttribute("position", new THREE.Float32BufferAttribute(skirtPos, 3));
  skirtGeo.setAttribute("color", new THREE.Float32BufferAttribute(skirtCol, 3));
  skirtGeo.setIndex(skirtIdx);
  skirtGeo.computeVertexNormals();
  const skirt = new THREE.Mesh(
    skirtGeo,
    new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9, metalness: 0.02 })
  );
  skirt.castShadow = true;
  skirt.receiveShadow = true;

  const linePos = [];
  [0.22, 0.4, 0.58, 0.74, 0.88].forEach((level) => {
    isolines(field, level).forEach(([a, b]) => {
      const pa = mapToWorld(a[0], a[1], level);
      const pb = mapToWorld(b[0], b[1], level);
      pa[1] += 0.006;
      pb[1] += 0.006;
      linePos.push(pa[0], pa[1], pa[2], pb[0], pb[1], pb[2]);
    });
  });
  const lines = new THREE.LineSegments(
    new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(linePos, 3)),
    new THREE.LineBasicMaterial({
      color: 0x2a3344,
      transparent: true,
      opacity: 0.22,
      depthWrite: false,
    })
  );

  land = new THREE.Group();
  land.add(mesh);
  land.add(skirt);
  land.add(lines);
  scene.add(land);
  readyMesh = true;
  return true;
}

function reset() {
  cam = { yaw: 0.62, pitch: 0.58, dist: 2.35 };
}

function orbit(dyaw, dpitch) {
  cam.yaw += dyaw;
  cam.pitch = Math.max(0.18, Math.min(1.28, cam.pitch + dpitch));
}

function dolly(factor) {
  cam.dist = Math.max(1.05, Math.min(4.8, cam.dist * factor));
}

function worldToScreen(x, y, z) {
  if (!camera) return { x: MAP_W / 2, y: MAP_H / 2, behind: true };
  updateCamera();
  const w = mapToWorld(x, y, z);
  _ndc.set(w[0], w[1], w[2]).project(camera);
  return {
    x: (_ndc.x * 0.5 + 0.5) * MAP_W,
    y: (1 - (_ndc.y * 0.5 + 0.5)) * MAP_H,
    behind: _ndc.z < -1 || _ndc.z > 1,
  };
}

function render() {
  if (!renderer || !scene || !camera || !readyMesh) return;
  resize();
  renderer.render(scene, camera);
}

window.Terrain3D = {
  init,
  ready,
  setField,
  reset,
  orbit,
  dolly,
  resize,
  render,
  worldToScreen,
};

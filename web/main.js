// Gothic complex preview: orbit view + first-person walk (WASD, mouse look), capsule collision against a
// three-mesh-bvh BVH of every solid triangle, scripted automatic doors/gates (hinged leaves swing open when you approach).
// Blender (x,y,z) -> glTF/three (x, z, -y).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { MeshBVH } from 'three-mesh-bvh';

const Q = new URLSearchParams(location.search);
const TEST = Q.has('test');
const MODEL = Q.get('model') || './building_opt.glb';
const b2t = (x, y, z) => new THREE.Vector3(x, z, -y);

const renderer = new THREE.WebGLRenderer({ antialias: !TEST, preserveDrawingBuffer: true });
renderer.setPixelRatio(TEST ? 1 : Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.AgXToneMapping; renderer.toneMappingExposure = 1.0;   // gap #8: AgX like the Cycles beauty render
renderer.shadowMap.enabled = !TEST; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
// gap #8: warm soft overcast matching ref/isometric.png and the Cycles beauty light (compare/mat/warm_light.json):
// warm off-white sky, light warm haze far out (keeps contrast), warm-beige hemisphere fill, soft warm-white key light
scene.background = new THREE.Color(0xd6cfc4);
scene.fog = new THREE.Fog(0xd6cfc4, 140, 560);
scene.add(new THREE.HemisphereLight(0xf4ece0, 0x5a5044, 1.3));
const sun = new THREE.DirectionalLight(0xfff1df, 2.3); sun.position.copy(b2t(-70, -90, 120));
sun.castShadow = !TEST; sun.shadow.mapSize.set(4096, 4096);
Object.assign(sun.shadow.camera, { left: -80, right: 80, top: 80, bottom: -80, near: 10, far: 400 }); sun.shadow.bias = -0.0004;
scene.add(sun); scene.add(sun.target);

const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.05, 2000);
const lamp = new THREE.PointLight(0xffe6c0, 0, 18, 1.6); camera.add(lamp); scene.add(camera);
camera.position.copy(b2t(-60, -110, 75));
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.target.copy(b2t(0, -2, 10)); orbit.enableDamping = true; orbit.update();

// ---------------- player ----------------
const R = 0.3, SEG = 1.0, EYE = 0.3;           // capsule radius / segment: feet .. feet+1.6 m, eyes at 1.6 m
const FEET = R + SEG;
const player = { pos: new THREE.Vector3(), vel: new THREE.Vector3(), yaw: 0, pitch: 0, onGround: false };
const keys = {};
let mode = 'orbit', bvh = null, SPACES = null;
const doors = [];
const SPEED = 4.0, GRAV = -20, OPEN_DIST = 3.2;
const feetY = () => player.pos.y - FEET;
function setFeet(v) { player.pos.set(v.x, v.y + FEET, v.z); player.vel.set(0, 0, 0); }

// ---------------- load ----------------
const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);
const [gltf, spaces] = await Promise.all([loader.loadAsync(MODEL), fetch('./spaces.json').then(r => r.json()).catch(() => null)]);
SPACES = spaces; scene.add(gltf.scene); scene.updateMatrixWorld(true);
const isLeaf = o => { while (o) { if (/^DoorLeaf_/.test(o.name)) return true; o = o.parent; } return false; };
// ruin decor (decals, small debris) is visual only: role "decor" (glTF extras) -> not in the collider
const isDecor = o => { while (o) { if (o.userData && o.userData.role === 'decor') return true; o = o.parent; } return false; };
{ // collider: every solid triangle in world space (door/gate leaves excluded: they are scripted)
  const parts = []; let nV = 0, nI = 0;
  gltf.scene.traverse(o => {
    if (!o.isMesh) return;
    o.castShadow = o.receiveShadow = !TEST;
    if (o.material && o.material.map) o.material.map.anisotropy = 4;
    if (o.material && /^Decal/i.test(o.material.name)) {   // alpha decals: blend over the wall, no depth write, pulled forward
      Object.assign(o.material, { transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 });
      o.castShadow = false; o.renderOrder = 2;
    }
    if (isLeaf(o) || isDecor(o)) return;
    parts.push(o); const g = o.geometry; nV += g.attributes.position.count; nI += g.index ? g.index.count : g.attributes.position.count;
  });
  const pos = new Float32Array(nV * 3), idx = new Uint32Array(nI); let vo = 0, io = 0; const v = new THREE.Vector3();
  for (const o of parts) {
    const g = o.geometry, p = g.attributes.position;
    for (let i = 0; i < p.count; i++) { v.fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld); pos.set([v.x, v.y, v.z], (vo + i) * 3); }
    if (g.index) for (let i = 0; i < g.index.count; i++) idx[io++] = g.index.getX(i) + vo; else for (let i = 0; i < p.count; i++) idx[io++] = i + vo;
    vo += p.count;
  }
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setIndex(new THREE.BufferAttribute(idx, 1));
  bvh = new MeshBVH(geo, { maxLeafSize: 12 }); geo.boundsTree = bvh; window.__colliderTris = io / 3;
}
// scripted doors: one entry per door record; its leaves rotate about their hinge (node origin) by swing * t
const leafByName = {}; gltf.scene.traverse(o => { if (/^DoorLeaf_/.test(o.name) && !leafByName[o.name]) leafByName[o.name] = o; });
if (SPACES) for (const d of SPACES.doors) {
  if (!d.leaves || !d.leaves.length) continue;
  const objs = d.leaves.map(n => leafByName[n] || leafByName[n.replace(/\./g, '')]).filter(Boolean);
  if (!objs.length) continue;
  doors.push({ id: d.id, c: b2t(...d.center), leaves: objs.map(o => ({ o, q0: o.quaternion.clone(), swing: (o.userData.swing ?? 1.5) })), t: 0 });
}
document.getElementById('load').remove();

// ---------------- collision helpers ----------------
const ray = new THREE.Ray();
function castFirst(o, d, far) { ray.origin.copy(o); ray.direction.copy(d).normalize(); const h = bvh.raycastFirst(ray, THREE.DoubleSide); return (h && h.distance <= far) ? h : null; }
const seg = new THREE.Line3(), tBox = new THREE.Box3(), tv = new THREE.Vector3(), tv2 = new THREE.Vector3();
const fwd = new THREE.Vector3(), right = new THREE.Vector3(), mv = new THREE.Vector3(), Y = new THREE.Vector3(0, 1, 0), qq = new THREE.Quaternion();
function step(dt) {
  fwd.set(-Math.sin(player.yaw), 0, -Math.cos(player.yaw)); right.set(-fwd.z, 0, fwd.x); mv.set(0, 0, 0);
  if (keys.KeyW) mv.add(fwd); if (keys.KeyS) mv.sub(fwd); if (keys.KeyD) mv.add(right); if (keys.KeyA) mv.sub(right);
  if (mv.lengthSq() > 0) mv.normalize().multiplyScalar(SPEED * (keys.ShiftLeft ? 1.8 : 1));
  if (player.onGround) player.vel.y = GRAV * dt; else player.vel.y += GRAV * dt;
  player.pos.addScaledVector(player.vel, dt); player.pos.addScaledVector(mv, dt);
  if (mv.lengthSq() > 0 && player.onGround) {        // step-up assist for risers <= 0.35 m
    const probe = tv.copy(player.pos).addScaledVector(tv2.copy(mv).normalize(), R + 0.12); probe.y = feetY() + 0.4;
    const h = castFirst(probe, tv2.set(0, -1, 0), 0.45);
    if (h) { const rise = h.point.y - feetY(); if (rise > 0.03 && rise < 0.35) player.pos.y += rise + 0.005; }
  }
  seg.start.copy(player.pos); seg.end.copy(player.pos).y -= SEG;
  tBox.makeEmpty(); tBox.expandByPoint(seg.start); tBox.expandByPoint(seg.end); tBox.min.addScalar(-R); tBox.max.addScalar(R);
  bvh.shapecast({ intersectsBounds: b => b.intersectsBox(tBox), intersectsTriangle: tri => {
    const d = tri.closestPointToSegment(seg, tv, tv2);
    if (d < R) { const depth = R - d; const dir = tv2.sub(tv).normalize(); seg.start.addScaledVector(dir, depth); seg.end.addScaledVector(dir, depth); } } });
  const delta = tv.subVectors(seg.start, player.pos);
  player.onGround = delta.y > Math.abs(dt * player.vel.y * 0.25);
  const off = Math.max(0, delta.length() - 1e-5); delta.normalize().multiplyScalar(off); player.pos.add(delta);
  if (!player.onGround) { delta.normalize(); player.vel.addScaledVector(delta, -delta.dot(player.vel)); } else player.vel.set(0, 0, 0);
  if (player.pos.y < -30) toStart();
}
function updateDoors(dt) {   // automatic doors: open while someone is within OPEN_DIST (walk mode), close otherwise
  for (const d of doors) {
    const near = mode === 'walk' && Math.hypot(player.pos.x - d.c.x, player.pos.z - d.c.z) < OPEN_DIST && Math.abs(feetY() - d.c.y) < 2.0;
    d.t = THREE.MathUtils.clamp(d.t + (near ? 1 : -1) * dt * 2.4, 0, 1);
    const a = THREE.MathUtils.smoothstep(d.t, 0, 1);
    for (const L of d.leaves) L.o.quaternion.copy(L.q0).multiply(qq.setFromAxisAngle(Y, L.swing * a));
  }
}

// ---------------- modes / input ----------------
const hud = document.getElementById('hud'), cross = document.getElementById('cross');
function toStart() { const p = SPACES ? SPACES.spaces.approach.probe : [0, -54, 0]; setFeet(b2t(p[0], p[1] - 1, p[2])); player.yaw = 0; player.pitch = 0.05; }
function setMode(m) {
  mode = m; document.getElementById('bOrbit').classList.toggle('on', m === 'orbit'); document.getElementById('bWalk').classList.toggle('on', m === 'walk');
  orbit.enabled = m === 'orbit'; lamp.intensity = m === 'walk' ? 6 : 0; cross.style.display = m === 'walk' ? 'block' : 'none';
  if (m === 'walk' && player.pos.lengthSq() === 0) toStart();
}
document.getElementById('bOrbit').onclick = () => { document.exitPointerLock?.(); setMode('orbit'); };
document.getElementById('bWalk').onclick = () => setMode('walk');
document.getElementById('bStart').onclick = () => { setMode('walk'); toStart(); };
renderer.domElement.addEventListener('click', () => { if (mode === 'walk' && !TEST) renderer.domElement.requestPointerLock?.(); });
document.addEventListener('mousemove', e => {
  if (mode !== 'walk' || document.pointerLockElement !== renderer.domElement) return;
  player.yaw -= e.movementX * 0.0022; player.pitch = THREE.MathUtils.clamp(player.pitch - e.movementY * 0.0022, -1.4, 1.4);
});
addEventListener('keydown', e => { keys[e.code] = true; if (e.code === 'Tab') { e.preventDefault(); setMode(mode === 'walk' ? 'orbit' : 'walk'); } });
addEventListener('keyup', e => { keys[e.code] = false; });
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
function syncCamera() { camera.position.set(player.pos.x, player.pos.y + EYE, player.pos.z); camera.rotation.set(player.pitch, player.yaw, 0, 'YXZ'); }
function where() {
  if (!SPACES) return '';
  const f = feetY(), x = player.pos.x, y = -player.pos.z; let best = null, bd = 1e9;
  for (const [k, s] of Object.entries(SPACES.spaces)) { if (Math.abs(s.z - f) > 1.6) continue; const d = Math.hypot(s.probe[0] - x, s.probe[1] - y); if (d < bd) { bd = d; best = k; } }
  return best || '';
}
function hudText() {
  const b = { x: player.pos.x.toFixed(1), y: (-player.pos.z).toFixed(1), z: feetY().toFixed(2) };
  return mode === 'walk'
    ? `漫游 WALK · WASD 移动 · 点击后鼠标转向 · Shift 跑 · Tab 切换<br>x ${b.x}  y ${b.y}  floor ${b.z} m · near: ${where()}`
    : `环绕 ORBIT · 左键旋转 · 滚轮缩放 · 右键平移 · Walk 进入漫游<br>collider tris: ${window.__colliderTris} · auto doors: ${doors.length}`;
}
let last = performance.now();
function loop(now) {
  const dt = Math.min((now - last) / 1000, 0.1); last = now;
  if (mode === 'walk') { const n = Math.ceil(dt / 0.01); for (let i = 0; i < n; i++) step(dt / n); syncCamera(); } else orbit.update();
  updateDoors(dt);
  hud.innerHTML = hudText();
  if (!TEST) renderer.render(scene, camera);
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

// ---------------- test hooks (walk/walk_test.py) ----------------
window.__walk = {
  ready: true, setMode, render() { syncCamera(); renderer.render(scene, camera); },
  teleport(x, y, z, yaw = 0) { setMode('walk'); setFeet(b2t(x, y, z)); player.yaw = yaw; player.onGround = false; },
  setYaw(y) { player.yaw = y; }, setPitch(p) { player.pitch = p; },
  state() { return { x: player.pos.x, y: -player.pos.z, z: feetY(), yaw: player.yaw, onGround: player.onGround, near: where() }; },
  doorsNear(r = 1.0) { return doors.filter(d => Math.hypot(player.pos.x - d.c.x, player.pos.z - d.c.z) < r && Math.abs(feetY() - d.c.y) < 2.0).map(d => ({ id: d.id, open: d.t })); },
  doorCount() { return doors.length; },
  raySegment(a, b) { const A = b2t(...a), B = b2t(...b); const d = B.clone().sub(A); const L = d.length(); if (L < 1e-6) return null; const h = castFirst(A, d, L); return h ? h.distance : null; },
  floorAt(x, y, z) { const h = castFirst(b2t(x, y, z + 1.0), new THREE.Vector3(0, -1, 0), 3.0); return h ? h.point.y : null; },
};

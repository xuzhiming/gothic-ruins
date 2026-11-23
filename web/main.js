// Gothic complex preview: orbit view + first-person walk (WASD, mouse look, grounded jump),
// optional noclip fly, capsule collision against a three-mesh-bvh of every solid triangle
// (including glass), scripted automatic doors/gates.
// Blender (x,y,z) -> glTF/three (x, z, -y).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { MeshBVH } from 'three-mesh-bvh';
import { applySurfacePolicy, isBlendedMaterial, isExactClearGlass } from './surface.js';

const Q = new URLSearchParams(location.search);
const TEST = Q.has('test');
const MODEL = Q.get('model') || './building_opt.glb';
const b2t = (x, y, z) => new THREE.Vector3(x, z, -y);

const renderer = new THREE.WebGLRenderer({ antialias: !TEST, preserveDrawingBuffer: true });
renderer.setPixelRatio(TEST ? 1 : Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.AgXToneMapping; renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = !TEST; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
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
let mode = 'orbit', fly = false, bvh = null, lid = null, SPACES = null;
let jumpQueued = false, jumpLock = 0;
let lastSafe = null;
const doors = [];
const SPEED = 4.0, GRAV = -20, OPEN_DIST = 3.2, JUMP = 4.1;
const FLY_SPEED = 8, FLY_BOOST = 2.5, FLY_R = 150, FLY_FEET_MIN = -15, FLY_FEET_MAX = 160;
const feetY = () => player.pos.y - FEET;
function setFeet(v) { player.pos.set(v.x, v.y + FEET, v.z); player.vel.set(0, 0, 0); }
function rememberSafe() {
  if (!lastSafe) lastSafe = { pos: new THREE.Vector3(), yaw: 0, pitch: 0 };
  lastSafe.pos.copy(player.pos); lastSafe.yaw = player.yaw; lastSafe.pitch = player.pitch;
}
function clearKeys() {
  for (const k of Object.keys(keys)) keys[k] = false;
  jumpQueued = false;
}

// ---------------- load ----------------
const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);
const [gltf, spaces] = await Promise.all([loader.loadAsync(MODEL), fetch('./spaces.json').then(r => r.json()).catch(() => null)]);
SPACES = spaces; scene.add(gltf.scene); scene.updateMatrixWorld(true);
const isLeaf = o => { while (o) { if (/^DoorLeaf_/.test(o.name)) return true; o = o.parent; } return false; };
const isDecor = o => { while (o) { if (o.userData && o.userData.role === 'decor') return true; o = o.parent; } return false; };
{ // collider: every solid triangle in world space (door/gate leaves and decor excluded; glass stays)
  const parts = []; let nV = 0, nI = 0;
  gltf.scene.traverse(o => {
    if (!o.isMesh) return;
    o.castShadow = o.receiveShadow = !TEST;
    if (o.material && o.material.map) o.material.map.anisotropy = 4;
    if (o.material && /^Decal/i.test(o.material.name)) {
      Object.assign(o.material, { transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 });
      o.castShadow = false; o.renderOrder = 2;
    }
    applySurfacePolicy(o);
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
const down = new THREE.Vector3(0, -1, 0);
function castFirst(o, d, far) {
  ray.origin.copy(o); ray.direction.copy(d).normalize();
  let best = null;
  const h = bvh.raycastFirst(ray, THREE.DoubleSide);
  if (h && h.distance <= far) best = h;
  if (lid) {
    const h2 = lid.raycastFirst(ray, THREE.DoubleSide);
    if (h2 && h2.distance <= far && (!best || h2.distance < best.distance)) best = h2;
  }
  return best;
}
const seg = new THREE.Line3(), tBox = new THREE.Box3(), tv = new THREE.Vector3(), tv2 = new THREE.Vector3(), hold = new THREE.Vector3();
const fwd = new THREE.Vector3(), right = new THREE.Vector3(), mv = new THREE.Vector3(), Y = new THREE.Vector3(0, 1, 0), qq = new THREE.Quaternion();
function pushCapsule(tree) {
  tree.shapecast({ intersectsBounds: b => b.intersectsBox(tBox), intersectsTriangle: tri => {
    const d = tri.closestPointToSegment(seg, tv, tv2);
    if (d < R) { const depth = R - d; const dir = tv2.sub(tv).normalize(); seg.start.addScaledVector(dir, depth); seg.end.addScaledVector(dir, depth); }
  } });
}
function capsuleBlocked(pos) {
  seg.start.copy(pos); seg.end.copy(pos).y -= SEG;
  tBox.makeEmpty(); tBox.expandByPoint(seg.start); tBox.expandByPoint(seg.end); tBox.min.addScalar(-R); tBox.max.addScalar(R);
  return bvh.shapecast({
    intersectsBounds: b => b.intersectsBox(tBox),
    intersectsTriangle: tri => tri.closestPointToSegment(seg, tv, tv2) < R - 1e-3,
  });
}
function headroomOK(feet, x, z) { return !castFirst(hold.set(x, feet + 0.05, z), Y, 1.65); }
function tryLanding(pos) {
  if (!capsuleBlocked(pos)) {
    const floor = castFirst(hold.set(pos.x, pos.y, pos.z), down, FEET + 0.5);
    if (floor && Math.abs(floor.point.y - (pos.y - FEET)) <= 0.4) {
      const next = pos.clone(); next.y = floor.point.y + FEET;
      if (!capsuleBlocked(next) && headroomOK(floor.point.y, next.x, next.z)) return next;
    }
  }
  const h = castFirst(hold.set(pos.x, pos.y, pos.z), down, 120);
  if (!h || h.point.y < -5) return null;
  const next = pos.clone(); next.y = h.point.y + FEET;
  if (capsuleBlocked(next) || !headroomOK(h.point.y, next.x, next.z)) return null;
  return next;
}
function step(dt) {
  fwd.set(-Math.sin(player.yaw), 0, -Math.cos(player.yaw)); right.set(-fwd.z, 0, fwd.x); mv.set(0, 0, 0);
  if (keys.KeyW) mv.add(fwd); if (keys.KeyS) mv.sub(fwd); if (keys.KeyD) mv.add(right); if (keys.KeyA) mv.sub(right);
  if (mv.lengthSq() > 0) mv.normalize().multiplyScalar(SPEED * (keys.ShiftLeft ? 1.8 : 1));
  let tookOff = false;
  if (jumpQueued) {
    if (player.onGround && jumpLock <= 0) { player.vel.y = JUMP; player.onGround = false; jumpLock = 0.12; tookOff = true; }
    jumpQueued = false;
  }
  if (!tookOff) {
    if (player.onGround && jumpLock <= 0) player.vel.y = GRAV * dt;
    else player.vel.y += GRAV * dt;
  }
  if (jumpLock > 0) jumpLock = Math.max(0, jumpLock - dt);
  if (player.vel.y > 0) {
    const h = castFirst(hold.set(player.pos.x, player.pos.y + R, player.pos.z), Y, player.vel.y * dt + 0.03);
    if (h) { const allow = Math.max(0, h.distance - 0.02); if (player.vel.y * dt > allow) player.vel.y = dt > 0 ? allow / dt : 0; }
  }
  player.pos.addScaledVector(player.vel, dt); player.pos.addScaledVector(mv, dt);
  if (mv.lengthSq() > 0 && player.onGround) {
    const probe = tv.copy(player.pos).addScaledVector(tv2.copy(mv).normalize(), R + 0.12); probe.y = feetY() + 0.4;
    const h = castFirst(probe, tv2.set(0, -1, 0), 0.45);
    if (h) { const rise = h.point.y - feetY(); if (rise > 0.03 && rise < 0.35) player.pos.y += rise + 0.005; }
  }
  seg.start.copy(player.pos); seg.end.copy(player.pos).y -= SEG;
  tBox.makeEmpty(); tBox.expandByPoint(seg.start); tBox.expandByPoint(seg.end); tBox.min.addScalar(-R); tBox.max.addScalar(R);
  pushCapsule(bvh); if (lid) pushCapsule(lid);
  const delta = tv.subVectors(seg.start, player.pos);
  player.onGround = delta.y > Math.abs(dt * player.vel.y * 0.25);
  if (jumpLock > 0) player.onGround = false;
  const off = Math.max(0, delta.length() - 1e-5); delta.normalize().multiplyScalar(off); player.pos.add(delta);
  if (!player.onGround) { delta.normalize(); player.vel.addScaledVector(delta, -delta.dot(player.vel)); } else player.vel.set(0, 0, 0);
  if (player.onGround) rememberSafe();
  if (player.pos.y < -30) toStart();
}
function stepFly(dt) {
  fwd.set(-Math.sin(player.yaw), 0, -Math.cos(player.yaw)); right.set(-fwd.z, 0, fwd.x); mv.set(0, 0, 0);
  if (keys.KeyW) mv.add(fwd); if (keys.KeyS) mv.sub(fwd); if (keys.KeyD) mv.add(right); if (keys.KeyA) mv.sub(right);
  let up = 0;
  if (keys.Space) up += 1;
  if (keys.KeyC) up -= 1;
  const sp = FLY_SPEED * ((keys.ShiftLeft || keys.ShiftRight) ? FLY_BOOST : 1);
  if (mv.lengthSq() > 0) mv.normalize().multiplyScalar(sp);
  player.vel.set(0, 0, 0); player.onGround = false;
  player.pos.addScaledVector(mv, dt); player.pos.y += up * sp * dt;
  const hy = Math.hypot(player.pos.x, player.pos.z);
  if (hy > FLY_R) { const s = FLY_R / hy; player.pos.x *= s; player.pos.z *= s; }
  player.pos.y = THREE.MathUtils.clamp(player.pos.y, FLY_FEET_MIN + FEET, FLY_FEET_MAX + FEET);
}
function updateDoors(dt) {
  for (const d of doors) {
    const near = mode === 'walk' && !fly && Math.hypot(player.pos.x - d.c.x, player.pos.z - d.c.z) < OPEN_DIST && Math.abs(feetY() - d.c.y) < 2.0;
    d.t = THREE.MathUtils.clamp(d.t + (near ? 1 : -1) * dt * 2.4, 0, 1);
    const a = THREE.MathUtils.smoothstep(d.t, 0, 1);
    for (const L of d.leaves) L.o.quaternion.copy(L.q0).multiply(qq.setFromAxisAngle(Y, L.swing * a));
  }
}

// ---------------- modes / input ----------------
const hud = document.getElementById('hud'), cross = document.getElementById('cross');
function toStart() {
  const p = SPACES ? SPACES.spaces.approach.probe : [0, -54, 0];
  setFeet(b2t(p[0], p[1] - 1, p[2])); player.yaw = 0; player.pitch = 0.05; player.onGround = false; rememberSafe();
}
function paintMode() {
  document.getElementById('bOrbit').classList.toggle('on', mode === 'orbit');
  document.getElementById('bWalk').classList.toggle('on', mode === 'walk' && !fly);
  document.getElementById('bFly').classList.toggle('on', fly);
  const show = mode === 'walk';
  document.getElementById('touch').classList.toggle('live', show);
  document.getElementById('tJump').hidden = !(show && !fly);
  document.getElementById('tUp').hidden = !(show && fly);
  document.getElementById('tDown').hidden = !(show && fly);
  if (hud) hud.innerHTML = hudText();
}
function exitFly() {
  fly = false; jumpQueued = false; player.vel.set(0, 0, 0);
  const landed = tryLanding(player.pos);
  if (landed) { player.pos.copy(landed); player.onGround = true; rememberSafe(); }
  else if (lastSafe) { player.pos.copy(lastSafe.pos); player.yaw = lastSafe.yaw; player.pitch = lastSafe.pitch; player.onGround = true; }
  else toStart();
  paintMode();
}
function enterFly() {
  if (mode !== 'walk') setMode('walk');
  if (player.pos.lengthSq() === 0) toStart();
  if (!lastSafe) rememberSafe();
  fly = true; player.vel.set(0, 0, 0); player.onGround = false; jumpQueued = false; jumpLock = 0;
  paintMode();
}
function setMode(m) {
  if (m !== 'walk' && fly) exitFly();
  mode = m;
  orbit.enabled = m === 'orbit'; lamp.intensity = m === 'walk' ? 6 : 0; cross.style.display = m === 'walk' ? 'block' : 'none';
  if (m === 'walk' && player.pos.lengthSq() === 0) toStart();
  paintMode();
}
function bindHold(id, code, onDown) {
  const b = document.getElementById(id);
  const down = (e) => { e.preventDefault(); keys[code] = true; if (onDown) onDown(); };
  const up = () => { keys[code] = false; };
  b.addEventListener('pointerdown', down);
  b.addEventListener('pointerup', up);
  b.addEventListener('pointercancel', up);
  b.addEventListener('pointerleave', up);
}
document.getElementById('bOrbit').onclick = () => { document.exitPointerLock?.(); setMode('orbit'); };
document.getElementById('bWalk').onclick = () => { if (fly) exitFly(); setMode('walk'); };
document.getElementById('bFly').onclick = () => { fly ? exitFly() : enterFly(); };
document.getElementById('bStart').onclick = () => { fly = false; jumpQueued = false; setMode('walk'); toStart(); };
bindHold('tJump', 'Space', () => { if (mode === 'walk' && !fly) jumpQueued = true; });
bindHold('tUp', 'Space');
bindHold('tDown', 'KeyC');
renderer.domElement.addEventListener('click', () => { if (mode === 'walk' && !TEST) renderer.domElement.requestPointerLock?.(); });
document.addEventListener('mousemove', e => {
  if (mode !== 'walk' || document.pointerLockElement !== renderer.domElement) return;
  player.yaw -= e.movementX * 0.0022; player.pitch = THREE.MathUtils.clamp(player.pitch - e.movementY * 0.0022, -1.4, 1.4);
});
addEventListener('keydown', e => {
  keys[e.code] = true;
  if (e.code === 'Space') {
    e.preventDefault();
    if (!e.repeat && mode === 'walk' && !fly) jumpQueued = true;
  }
  if (e.code === 'Tab') { e.preventDefault(); setMode(mode === 'walk' ? 'orbit' : 'walk'); }
  if (e.code === 'KeyF' && !e.repeat) { if (fly) exitFly(); else enterFly(); }
});
addEventListener('keyup', e => { keys[e.code] = false; if (e.code === 'Space') e.preventDefault(); });
addEventListener('blur', clearKeys);
document.addEventListener('visibilitychange', () => { if (document.hidden) clearKeys(); });
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
  const pos = `<br>x ${b.x}  y ${b.y}  floor ${b.z} m · near: ${where()}`;
  if (mode !== 'walk') return `环绕 ORBIT · 左键旋转 · 滚轮缩放 · 右键平移 · Walk 进入漫游<br>collider tris: ${window.__colliderTris} · auto doors: ${doors.length}`;
  if (fly) return `飞行 FLY · WASD 平移 · Space 上升 · C 下降 · Shift 加速 · F 回到步行 · Tab 环绕${pos}`;
  return `漫游 WALK · WASD 移动 · 点击后鼠标转向 · Space 跳 · Shift 跑 · F 飞行 · Tab 切换${pos}`;
}
let last = performance.now();
function loop(now) {
  const dt = Math.min((now - last) / 1000, 0.1); last = now;
  if (mode === 'walk') {
    const n = Math.ceil(dt / 0.01);
    for (let i = 0; i < n; i++) (fly ? stepFly : step)(dt / n);
    syncCamera();
  } else orbit.update();
  updateDoors(dt);
  hud.innerHTML = hudText();
  if (!TEST) renderer.render(scene, camera);
  requestAnimationFrame(loop);
}
paintMode();
requestAnimationFrame(loop);

function plainMat(desc) {
  return {
    name: desc.materialName || '',
    transparent: !!desc.transparent,
    opacity: desc.opacity ?? 1,
    depthWrite: desc.depthWrite !== false,
    userData: { alphaMode: desc.alphaMode || '', role: desc.materialRole || '' },
  };
}
function glassSample() {
  let meshes = 0, excluded = 0, rayHit = false, sample = null;
  gltf.scene.updateMatrixWorld(true);
  gltf.scene.traverse(o => {
    if (!o.isMesh || !o.userData || o.userData.role !== 'glass') return;
    meshes++;
    if (isLeaf(o) || isDecor(o)) excluded++;
    if (rayHit) return;
    const g = o.geometry, p = g.attributes.position;
    const nTri = g.index ? g.index.count / 3 : p.count / 3;
    for (let t = 0; t < nTri && !rayHit && t < 8; t++) {
      const ia = g.index ? g.index.getX(t * 3) : t * 3;
      const ib = g.index ? g.index.getX(t * 3 + 1) : t * 3 + 1;
      const ic = g.index ? g.index.getX(t * 3 + 2) : t * 3 + 2;
      const a = new THREE.Vector3().fromBufferAttribute(p, ia).applyMatrix4(o.matrixWorld);
      const b = new THREE.Vector3().fromBufferAttribute(p, ib).applyMatrix4(o.matrixWorld);
      const c = new THREE.Vector3().fromBufferAttribute(p, ic).applyMatrix4(o.matrixWorld);
      const ab = b.clone().sub(a), ac = c.clone().sub(a), n = ab.cross(ac);
      if (n.lengthSq() < 1e-8) continue;
      n.normalize();
      const cent = a.add(b).add(c).multiplyScalar(1 / 3);
      const origin = cent.clone().addScaledVector(n, 0.2);
      const h = castFirst(origin, n.clone().negate(), 0.5);
      sample = { hit: h ? h.distance : null };
      if (h && h.distance > 0.02 && h.distance < 0.35) rayHit = true;
    }
  });
  return { meshes, excluded, rayHit, sample };
}

window.__walk = {
  ready: true, setMode, render() { syncCamera(); renderer.render(scene, camera); },
  teleport(x, y, z, yaw = 0) { fly = false; jumpQueued = false; jumpLock = 0; setMode('walk'); setFeet(b2t(x, y, z)); player.yaw = yaw; player.onGround = false; },
  setYaw(y) { player.yaw = y; }, setPitch(p) { player.pitch = p; },
  state() { return { x: player.pos.x, y: -player.pos.z, z: feetY(), yaw: player.yaw, onGround: player.onGround, near: where(), mode, fly }; },
  doorsNear(r = 1.0) { return doors.filter(d => Math.hypot(player.pos.x - d.c.x, player.pos.z - d.c.z) < r && Math.abs(feetY() - d.c.y) < 2.0).map(d => ({ id: d.id, open: d.t })); },
  doorCount() { return doors.length; },
  raySegment(a, b) { const A = b2t(...a), B = b2t(...b); const d = B.clone().sub(A); const L = d.length(); if (L < 1e-6) return null; const h = castFirst(A, d, L); return h ? h.distance : null; },
  floorAt(x, y, z) { const h = castFirst(b2t(x, y, z + 1.0), down, 3.0); return h ? h.point.y : null; },
  setFly(v) { if (v) enterFly(); else if (fly) exitFly(); },
  placeFly(x, y, z) { if (!fly) throw new Error('placeFly requires fly'); const p = b2t(x, y, z); player.pos.set(p.x, p.y + FEET, p.z); },
  blocked(x, y, z) { const p = b2t(x, y, z); p.y += FEET; return capsuleBlocked(p); },
  sealOverhead(gap = 0.22) {
    const y = player.pos.y + R + gap, x = player.pos.x, z = player.pos.z, s = 1.5;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([
      x - s, y, z - s, x + s, y, z - s, x + s, y, z + s, x - s, y, z + s,
    ]), 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    lid = new MeshBVH(g, { maxLeafSize: 8 }); g.boundsTree = lid;
    return y;
  },
  clearLid() { lid = null; },
  clearInput: clearKeys,
  classifySurface(desc) {
    const mat = plainMat(desc);
    return { blended: isBlendedMaterial(mat), exactGlass: mat.name === 'Glass', realGlass: isExactClearGlass(mat) };
  },
  applyPolicy(desc) {
    const mat = plainMat(desc);
    const mesh = { name: desc.meshName || '', userData: { role: desc.role || '' }, material: mat, castShadow: true, receiveShadow: true, renderOrder: desc.renderOrder || 0 };
    applySurfacePolicy(mesh);
    return { castShadow: mesh.castShadow, receiveShadow: mesh.receiveShadow, renderOrder: mesh.renderOrder, transparent: mat.transparent, opacity: mat.opacity, depthWrite: mat.depthWrite, depthTest: mat.depthTest !== false };
  },
  surfaces() {
    const rows = [];
    gltf.scene.traverse(o => {
      if (!o.isMesh) return;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const mat of mats) {
        if (!mat) continue;
        rows.push({
          mesh: o.name, role: (o.userData && o.userData.role) || '', material: mat.name || '',
          transparent: !!mat.transparent, opacity: mat.opacity, depthWrite: mat.depthWrite, depthTest: mat.depthTest !== false,
          roughness: mat.roughness, metalness: mat.metalness, side: mat.side,
          castShadow: o.castShadow, receiveShadow: o.receiveShadow, renderOrder: o.renderOrder,
          blended: isBlendedMaterial(mat), realGlass: isExactClearGlass(mat),
        });
      }
    });
    return rows;
  },
  lookAt(ex, ey, ez, tx, ty, tz) {
    fly = false; jumpQueued = false; setMode('walk');
    player.pos.set(ex, ez - EYE, -ey); player.vel.set(0, 0, 0);
    const dx = tx - ex, dy = ty - ey, dz = tz - ez, h = Math.hypot(dx, dy) || 1e-6;
    player.yaw = Math.atan2(-dx, dy);
    player.pitch = THREE.MathUtils.clamp(-Math.atan2(dz, h), -1.2, 1.2);
    syncCamera();
  },
  viewProbes() {
    const take = (pred, limit) => {
      const out = [];
      gltf.scene.updateMatrixWorld(true);
      gltf.scene.traverse(o => {
        if (!o.isMesh || out.length >= limit) return;
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        if (!pred(o, mats)) return;
        const g = o.geometry, p = g.attributes.position;
        const nTri = Math.floor(g.index ? g.index.count / 3 : p.count / 3);
        if (!nTri) return;
        for (const f of [0.15, 0.4, 0.62, 0.85]) {
          if (out.length >= limit) break;
          const t = Math.min(nTri - 1, Math.floor(nTri * f));
          const ia = g.index ? g.index.getX(t * 3) : t * 3;
          const ib = g.index ? g.index.getX(t * 3 + 1) : t * 3 + 1;
          const ic = g.index ? g.index.getX(t * 3 + 2) : t * 3 + 2;
          const a = new THREE.Vector3().fromBufferAttribute(p, ia).applyMatrix4(o.matrixWorld);
          const b = new THREE.Vector3().fromBufferAttribute(p, ib).applyMatrix4(o.matrixWorld);
          const c = new THREE.Vector3().fromBufferAttribute(p, ic).applyMatrix4(o.matrixWorld);
          const n = b.clone().sub(a).cross(c.clone().sub(a));
          if (n.lengthSq() < 1e-10) continue;
          n.normalize();
          const cent = a.add(b).add(c).multiplyScalar(1 / 3);
          out.push({
            mesh: o.name, material: (mats.find(m => m && m.name === 'Glass') || mats[0]).name,
            x: cent.x, y: -cent.z, z: cent.y, nx: n.x, ny: -n.z, nz: n.y,
          });
        }
      });
      return out;
    };
    return {
      glass: take((o, mats) => mats.some(m => isExactClearGlass(m)), 8),
      blind: take((o, mats) => mats.some(m => m && m.name === 'Glass_blind'), 4),
      decal: take((o, mats) => mats.some(m => m && /^Decal/i.test(m.name || '')), 4),
    };
  },
  glassSample,
};

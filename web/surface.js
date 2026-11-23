// Real glass is role "glass" plus an exported blend signal.
// Names are ignored, so blind windows and opaque Glass_* materials stay opaque.

export function alphaModeOf(mat) {
  const ud = (mat && mat.userData) || {};
  return ud.alphaMode || ud.alpha_mode || '';
}

export function isBlendedMaterial(mat) {
  if (!mat) return false;
  const mode = alphaModeOf(mat);
  if (mode === 'OPAQUE' || mode === 'MASK') return false;
  if (mode === 'BLEND') return true;
  if (typeof mat.opacity === 'number' && mat.opacity < 0.999) return true;
  if (mat.transparent === true && mat.depthWrite === false) return true;
  return false;
}

export function hasGlassRole(mesh, mat) {
  const role = (mesh && mesh.userData && mesh.userData.role) || (mat && mat.userData && mat.userData.role) || '';
  return role === 'glass';
}

export function isRealGlass(mesh, mat) {
  return hasGlassRole(mesh, mat) && isBlendedMaterial(mat);
}

// Keep exported opacity and color. Transparent glass skips the depth buffer and shadow maps
// so the wall behind it stays visible; renderOrder 1 sits after opaque walls and before decals.
export function applySurfacePolicy(mesh) {
  const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  let real = false;
  for (const mat of mats) {
    if (!mat || /^Decal/i.test(mat.name || '')) continue;
    if (!isRealGlass(mesh, mat)) continue;
    real = true;
    mat.transparent = true;
    mat.depthWrite = false;
  }
  if (real) {
    mesh.castShadow = false;
    mesh.renderOrder = Math.max(mesh.renderOrder || 0, 1);
  }
  return real;
}

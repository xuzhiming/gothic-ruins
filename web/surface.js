// Clear glass is the material whose name is exactly "Glass".
// Glass_blind and any other name that merely contains "Glass" stay untouched.

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

// Exact exported pane. An opaque material that happens to be named Glass is not forced transparent.
export function isExactClearGlass(mat) {
  return !!(mat && mat.name === 'Glass' && isBlendedMaterial(mat));
}

// Depth write and shadow casting are per the glass contract. Opacity, color, and the map stay
// as the GLB exported them. renderOrder is left alone so decals (renderOrder 2) keep their order.
export function applySurfacePolicy(mesh) {
  const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  let clear = 0;
  let other = 0;
  for (const mat of mats) {
    if (!mat || /^Decal/i.test(mat.name || '')) continue;
    if (!isExactClearGlass(mat)) {
      if (mat.name) other++;
      continue;
    }
    clear++;
    mat.transparent = true;
    mat.depthWrite = false;
    mat.depthTest = true;
  }
  if (clear && !other) {
    mesh.castShadow = false;
    mesh.receiveShadow = false;
  }
  return clear > 0;
}

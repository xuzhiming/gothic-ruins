# Web coordination contract (asset-only glass task)

No web source changes were made by this task.

- Transparent glTF material exact name: `Glass`. Match `material.name === "Glass"`, including entries of material arrays. Do not match all names beginning with Glass.
- Opaque glTF material exact name: `Glass_blind` (facade blind lancets + tympanum). Keep opaque/depthWrite/shadows unchanged.
- Transparent mesh node: `Glass_glass`, extras `{role:"glass",group:"Glass"}`. Keep in collision BVH. Glass transparency must NOT allow walking/flying through intact panes.
- Exported Glass: alphaMode BLEND, alpha .24, metallic 0, roughness .09, doubleSided true, grey-green RGB image `glass_clear`; transmission 0 (no KHR_materials_transmission). IOR 1.5 is default and may be omitted from glTF. This is thin alpha transparency, not refraction.
- Runtime recommendation for Glass only: `transparent=true; depthWrite=false; castShadow=false;` retain ordinary depthTest. Evaluate receiveShadow=false to avoid fake opaque shadows on glass. Material color/map/opacity should come from the GLB, not a second arbitrary override.
- Do not globally force renderOrder=2 or hide back walls. Check glass against Decal_* (existing renderOrder=2) and opaque room geometry; a single merged multi-pane mesh cannot guarantee ideal intersecting-transparent sorting. Prefer normal loader ordering initially and visual regressions, then split panes only if a real artifact is reproduced.
- The historical local browser harness does not inspect sorting/shadows/translucency. No browser was controlled or production tested for t22. Production reportedly includes 8bca20e; its runtime may differ from local web sources. Do not infer production behavior from the old local viewer. End-to-end transparency/sorting/shadow/collision acceptance is pending parent/cloud verification.

Known retained obstruction: E4 rear dormer (audit id House_E4_dormer_29) overlaps an original chimney. The wall is cut, but that pane does not have a clear view past the chimney. Chimney geometry is preserved exactly; moving/removing it is outside the approved structural scope.

Full t22 window enumeration, all retained structural obstructions and decisions: `docs/window-audit-t22.md` and `window-audit/windows_all.json.gz`. E2 also has a partly chimney-occluded rear dormer; E4 is not the only partially obscured window.

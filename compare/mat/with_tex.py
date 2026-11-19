"""blender -b X.blend -P compare/mat/with_tex.py -- TEXDIR <render_beauty args...>: re-point every image to TEXDIR (e.g. the
pre-gap-#7 texture set) and run src/render_beauty.py with the remaining args (before/after renders of the same blend)."""
import bpy, sys, os
a = sys.argv[sys.argv.index("--") + 1:]; texdir = os.path.abspath(a[0])
for im in bpy.data.images:
    if im.filepath:
        p = os.path.join(texdir, os.path.basename(im.filepath))
        if os.path.exists(p): im.filepath = p; im.reload()
sys.argv = [sys.argv[0], "--"] + a[1:]
exec(compile(open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "render_beauty.py")).read(), "render_beauty.py", "exec"))

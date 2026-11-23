"""Deterministic through-hole panels and roof clipping, with no random draws."""
from mathutils import Vector
from mathutils.geometry import tessellate_polygon, barycentric_transform
import geom
RECORDS=[]

def panel(bk, outer, holes, o, S, T, thickness):
    """Extrude a polygon with inner loops; preserve original boundary and UV mapping."""
    loops=[geom.ccw(outer)]+[geom.ccw(h)[::-1] for h in holes]
    o,S,T=Vector(o),Vector(S),Vector(T); N=S.cross(T).normalized()
    flat=[p for lp in loops for p in lp]
    f=[o+S*x+T*y+N*thickness/2 for x,y in flat]
    b=[v-N*thickness for v in f]
    for a,c,d in tessellate_polygon([[Vector((x,y,0)) for x,y in lp] for lp in loops]):
        if (f[c]-f[a]).cross(f[d]-f[a]).dot(N)<0: c,d=d,c
        bk.face([f[a],f[c],f[d]]); bk.face([b[d],b[c],b[a]])
    k=0
    for lp in loops:
        for i in range(len(lp)):
            a=k+i; c=k+(i+1)%len(lp)
            bk.face([b[a],b[c],f[c],f[a]])
        k+=len(lp)

def record(name,center,normal,along,half_depth,kind):
    RECORDS.append(dict(id=name,center=list(center),normal=list(normal),along=list(along),half_depth=half_depth,kind=kind))

def gable(bk,p0,p1,z0,apex,thickness,openings=()):
    p0,p1=Vector((*p0,0)),Vector((*p1,0)); S=(p1-p0).normalized(); L=(p1-p0).length
    holes=[[(a,lo-z0),(b,lo-z0),(b,hi-z0),(a,hi-z0)] for a,b,lo,hi in openings]
    panel(bk,[(0,0),(L,0),(L/2,apex-z0)],holes,p0+Vector((0,0,z0)),S,(0,0,1),thickness)
    for i,(a,b,lo,hi) in enumerate(openings):
        record(bk.group+'_gable_'+str(len(RECORDS)), p0+S*((a+b)/2)+Vector((0,0,(lo+hi)/2)),S.cross(Vector((0,0,1))),S,thickness/2,'gable')

def _split(poly,n,d):
    """Partition convex/planar polygon on n.dot(p)<=d into inside and outside."""
    inside=[]; outside=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=n.dot(a)-d; db=n.dot(b)-d
        (inside if da<=1e-7 else outside).append(a)
        if (da < -1e-7 and db>1e-7) or (db < -1e-7 and da>1e-7):
            q=a+(b-a)*(da/(da-db)); inside.append(q); outside.append(q)
    return inside,outside

def clip_new_roof(bk,start,footprints):
    """Subtract dormer interior vertical prisms only from newly emitted roof faces.
    Faces outside each footprint are retained byte-for-byte; caps are hidden in side walls.
    """
    if not footprints: return
    old=bk.f[start:]; bk.f=bk.f[:start]
    for face in old:
        pieces=[[bk.v[i] for i in face]]
        for planes in footprints:
            result=[]
            for poly in pieces:
                # A separating plane proves no intersection: preserve the whole
                # original face and its UVs, rather than tessellating empty space.
                if len(planes)>4 and any(all(n.dot(v)-d>1e-7 for v in poly) for n,d in planes):
                    result.append(poly); continue
                inside=poly
                for n,d in planes:
                    inside,outside=_split(inside,n,d)
                    if len(outside)>=3: result.append(outside)
                    if len(inside)<3: break
            pieces=result
        original=[bk.v[i] for i in face]
        if len(pieces)==1 and len(pieces[0])==len(original) and all((a-b).length<1e-7 for a,b in zip(pieces[0],original)):
            bk.f.append(face)
        else:
            for poly in pieces:
                if geom.newell(poly).length<1e-10: continue
                uv=[Vector((*bk.uv[i],0)) for i in face[:3]]
                mapped=[barycentric_transform(v,*original[:3],*uv) for v in poly]
                bk.face_uv(poly,[(v.x,v.y) for v in mapped])

    # build.make_obj writes UVs by loop order, so discard orphan vertices and
    # expand the surviving faces back to the Bucket invariant (one vertex per loop).
    oldv,oldu,oldf=bk.v,bk.uv,bk.f
    bk.v=[]; bk.uv=[]; bk.f=[]
    for f in oldf:
        k=len(bk.v); bk.v.extend(oldv[i] for i in f); bk.uv.extend(oldu[i] for i in f)
        bk.f.append(tuple(range(k,k+len(f))))

def roof_footprint(fr,u0,u1,v0,v1):
    origin=fr.M(0,0); u=fr.dir(1,0); v=fr.dir(0,1)
    return [(u,u.dot(origin)+u1),(-u,(-u).dot(origin)-u0),(v,v.dot(origin)+v1),(-v,(-v).dot(origin)-v0)]


def convex_prism(poly,o,S,T):
    """Outward half-planes of a convex 2-D hole, extruded along its normal."""
    poly=geom.ccw(poly);o,S,T=Vector(o),Vector(S),Vector(T);planes=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        n=S*(b[1]-a[1])-T*(b[0]-a[0])
        planes.append((n,n.dot(o+S*a[0]+T*a[1])))
    return planes

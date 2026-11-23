"""Shared metric t24u layout: no Blender imports or random state."""
def row_layout(houses, side):
    hs=[dict(h) for h in houses['list'] if h['row']==side]
    cfg=houses.get('alleys',{});enabled=cfg.get('enabled',False)
    gap=cfg['net_width']+2*cfg['finish_allowance'] if enabled else 0.
    north=houses['row_y'][1];south=cfg.get('south_datums',{}).get(side,houses['row_y'][0])
    usable=north-south-gap*(len(hs)-1);total=sum(h['w_px'] for h in hs)
    for i,h in enumerate(hs):
        h['w']=round(usable*h['w_px']/total,6) if enabled else h['w']
        h['north']=north;h['south']=round(north-h['w'],6)
        if enabled and i==len(hs)-1:h['south']=south;h['w']=round(north-south,6)
        north=h['south']-gap
    return hs

def partition_v(houses,width):
    return min(houses['partition_door_v'],width-1.15)

def alley_routes(P):
    H=P['houses'];cfg=H.get('alleys',{})
    if not cfg.get('enabled'):return []
    z=P['site']['plaza_z'];outer=P['site']['main'][1];back=H['row_x'][1]
    rx=(back+.12+outer-cfg['guard_thickness'])/2
    yn=H['row_y'][1]+cfg['north_platform_depth']/2;result=[]
    for side,sg in [('W',-1),('E',1)]:
        hs=row_layout(H,side)
        for i,(a,b) in enumerate(zip(hs,hs[1:])):
            y=(a['south']+b['north'])/2
            result.append(dict(id=f'alley_{side}{i}{i+1}',kind='alley',side=side,net_width=cfg['net_width'],path=[[sg*19.,y,z],[sg*rx,y,z]]))
        result.append(dict(id=f'rear_{side}',kind='rear',side=side,net_width=1.4,path=[[sg*rx,H['row_y'][0]+.65,z],[sg*rx,yn,z]]))
        # The NEW platform has 1.4m swept width. Beyond x=18 the existing
        # NW/NE-to-cathedral diagonal pinch admits the .60m player, NOT 1.4m.
        # These existing-road points were measured by BVH grid search, no assets moved.
        join=[(18.,yn),(15.75,yn),(15.75,36.05),(15.7,36.05),(15.7,36.2),(15.65,36.2),(15.65,36.25),(15.6,36.25),(15.6,36.3),(15.45,36.3),(15.45,36.35),(12.5,36.35),(12.5,44.)]
        path=[[sg*rx,yn,z]]+[[sg*x,y,z] for x,y in join]
        result.append(dict(id=f'turn_{side}',kind='north_turn',side=side,net_width=1.4,segment_widths=[1.4]+[.6]*(len(path)-2),path=path))
    return result

def guard_boxes(P):
    H=P['houses'];c=H['alleys'];s=P['site'];outer=s['main'][1];t=c['guard_thickness'];yn=H['row_y'][1];yt=yn+c['north_platform_depth'];ys=H['row_y'][0]
    boxes=[]
    for side,sg in [('W',-1),('E',1)]:
        def add(name,x0,x1,y0,y1):
            a,b=sorted([sg*x0,sg*x1]);boxes.append(dict(id=f'{side}_{name}',bounds=[a,b,y0,y1],height=c['guard_height']))
        add('outer',outer-t,outer,ys,yt)
        add('south',H['row_x'][1]-.04,outer,ys,ys+t)
        add('north',28.5,outer,yt-t,yt)
    return boxes

def ground_window_centers(houses,h):
    """Keep original GF slot selection; reflow only if fixed pad/skip loses a slot.

    Old 1.5m center exclusion was aesthetic, not an opening width. Scaling the
    original selected centers retains each opening with >.1m masonry to the door.
    """
    n=h['win'][0];W=h['w'];dv=min(max(h['door']*W,1.4),W-1.4)
    current=[1.2+(W-2.4)*(i+.5)/n for i in range(n)]
    current=[x for x in current if abs(x-dv)>1.5]
    peers=[v for v in houses['list'] if v['row']==h['row']]
    L=houses['row_y'][1]-houses['row_y'][0]
    oldw=round(L*h['w_px']/sum(v['w_px'] for v in peers),3)
    olddv=min(max(h['door']*oldw,1.4),oldw-1.4)
    old=[1.2+(oldw-2.4)*(i+.5)/n for i in range(n)]
    old=[x for x in old if abs(x-olddv)>1.5]
    return current if len(current)==len(old) else [x*W/oldw for x in old]

def preserve_window_damage(houses,hid,component,floor,orientation,ops):
    """Original asset's semantic ruin states, independent of rescaled weather draws."""
    states=houses.get('window_damage',{}).get(f'{hid}/{component}/F{floor}/{orientation}')
    if states is None:return ops
    glass=[o for o in ops if o.get('glass')]
    if len(glass)!=len(states):raise ValueError(('changed original window slot count',hid,component,floor,len(glass),len(states)))
    for o,missing in zip(glass,states):o['pane_missing']=missing
    return ops

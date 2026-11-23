"""Read GLB JSON and verify self-describing transparent vs blind glass."""
import json,struct,sys,os
report={}
for path in sys.argv[1:]:
 with open(path,'rb') as f:
  f.read(12); n,kind=struct.unpack('<II',f.read(8)); doc=json.loads(f.read(n))
 mats={m.get('name'):m for m in doc['materials']}; g=mats['Glass']; blind=mats['Glass_blind']
 p=g['pbrMetallicRoughness']
 assert g.get('alphaMode')=='BLEND',g
 assert p.get('metallicFactor',1)==0,p
 assert .15<p.get('baseColorFactor',[1]*4)[3]<.32,p
 assert .04<p.get('roughnessFactor',1)<.15,p
 assert g.get('doubleSided') is True,g
 assert blind.get('alphaMode','OPAQUE')=='OPAQUE',blind
 assert not g.get('extensions',{}).get('KHR_materials_transmission'),g
 glassnodes=[n for n in doc['nodes'] if n.get('extras',{}).get('role')=='glass']
 assert len(glassnodes)==1,glassnodes
 report[path]={'PASS':True,'bytes':os.path.getsize(path),'Glass':g,'Glass_blind':blind,'role_glass_nodes':len(glassnodes)}
print(json.dumps(report,indent=2))

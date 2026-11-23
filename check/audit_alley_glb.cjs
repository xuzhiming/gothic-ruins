// Offline decode: colliding guards and safe deck geometry survived raw/optimized export.
const fs=require('fs'),path=require('path');
const mods=path.resolve(__dirname,'../tools/gltf/node_modules');
const {NodeIO}=require(path.join(mods,'@gltf-transform/core'));
const {ALL_EXTENSIONS}=require(path.join(mods,'@gltf-transform/extensions'));
const {MeshoptDecoder}=require(path.join(mods,'meshoptimizer'));
(async()=>{await MeshoptDecoder.ready;const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const root=process.argv[2],expected=JSON.parse(fs.readFileSync(process.argv[3])),out={};
for(const file of ['building.glb','web/building_opt.glb']){
 const doc=await io.read(path.join(root,file));const rows=[];const allpoints=[];
 for(const n of doc.getRoot().listNodes()){
  if(!n.getMesh())continue;const m=n.getWorldMatrix();
  for(const p of n.getMesh().listPrimitives()){
   const pos=p.getAttribute('POSITION');
   for(let i=0;i<pos.getCount();i++){const [x,y,z]=pos.getElement(i,[]);const X=m[0]*x+m[4]*y+m[8]*z+m[12],Y=m[1]*x+m[5]*y+m[9]*z+m[13],Z=m[2]*x+m[6]*y+m[10]*z+m[14];if(Y>=4.199&&Y<=6.301&&Math.abs(X)>=20.5&&Math.abs(X)<=31.1)allpoints.push([X,-Z,Y]);}
  }
 }
 const lanes=JSON.parse(fs.readFileSync(process.argv[5]));const net=[];
 for(const lane of lanes){let south=Infinity,north=Infinity;
  for(const p of allpoints){if(Math.sign(p[0])!==lane.sign)continue;const dy=p[1]-lane.y;if(dy>0&&dy<.8)north=Math.min(north,dy);if(dy<0&&dy>-.8)south=Math.min(south,-dy);}
  const width=south+north;if(!Number.isFinite(width)||width<1.4-.0001)throw new Error(file+' as-exported net alley under1.4m '+lane.id+' '+width);
  net.push({id:lane.id,width_including_visual_decor_m:width});
 }

 for(const g of expected){
  const node=doc.getRoot().listNodes().find(n=>n.getName().startsWith('AlleyGuard_'+g.id+'_'));
  if(!node)throw new Error(file+' missing colliding guard '+g.id);
  if(node.getExtras().role!=='solid')throw new Error('guard role is not solid');
  const m=node.getWorldMatrix(),pts=[];
  for(const p of node.getMesh().listPrimitives()){
   const pos=p.getAttribute('POSITION');if(p.getIndices().getCount()<30)throw new Error('incomplete guard triangles');
   for(let i=0;i<pos.getCount();i++){const [x,y,z]=pos.getElement(i,[]);const X=m[0]*x+m[4]*y+m[8]*z+m[12],Y=m[1]*x+m[5]*y+m[9]*z+m[13],Z=m[2]*x+m[6]*y+m[10]*z+m[14];pts.push([X,-Z,Y]);}
  }
  const lo=[0,1,2].map(k=>Math.min(...pts.map(p=>p[k]))),hi=[0,1,2].map(k=>Math.max(...pts.map(p=>p[k])));
  const [x0,x1,y0,y1]=g.bounds;const wantLo=[x0,y0,4.2],wantHi=[x1,y1,4.2+g.height];
  if(lo.some((v,k)=>Math.abs(v-wantLo[k])>.006)||hi.some((v,k)=>Math.abs(v-wantHi[k])>.006))throw new Error(file+' guard bounds changed '+g.id);
  rows.push({id:g.id,role:node.getExtras().role,min:lo,max:hi});
 }
 out[file]={PASS:true,guards:rows,net_clearances:net};
}
fs.writeFileSync(process.argv[4],JSON.stringify(out,null,2));console.log('ALLEY GLB PASS',JSON.stringify(Object.keys(out)));
})().catch(e=>{console.error(e.message);process.exit(1)});

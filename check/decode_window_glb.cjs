// Offline GLB decode of every actual exported window triangle; no browser/network.
const path=require('node:path'),fs=require('node:fs');
const modules=path.resolve(__dirname,'../tools/gltf/node_modules');
const {NodeIO}=require(path.join(modules,'@gltf-transform/core'));
const {ALL_EXTENSIONS}=require(path.join(modules,'@gltf-transform/extensions'));
const {MeshoptDecoder}=require(path.join(modules,'meshoptimizer'));
(async()=>{await MeshoptDecoder.ready;const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const root=process.argv[2],out=process.argv[3],all={};
for(const name of ['building.glb','web/building_opt.glb']){
 const d=await io.read(path.join(root,name)),verts=[],faces=[],materials=[];
 for(const node of d.getRoot().listNodes()){
  const mesh=node.getMesh();if(!mesh)continue;const m=node.getWorldMatrix();
  for(const p of mesh.listPrimitives()){
   const mat=p.getMaterial();if(!mat||!['Glass','Glass_blind'].includes(mat.getName()))continue;
   const base=verts.length,pos=p.getAttribute('POSITION'),ids=p.getIndices().getArray();
   for(let i=0;i<pos.getCount();i++){const v=pos.getElement(i,[]);let x=v[0],y=v[1],z=v[2];let wx=m[0]*x+m[4]*y+m[8]*z+m[12],wy=m[1]*x+m[5]*y+m[9]*z+m[13],wz=m[2]*x+m[6]*y+m[10]*z+m[14];verts.push([wx,-wz,wy]);}
   for(let i=0;i<ids.length;i+=3){faces.push([base+ids[i],base+ids[i+1],base+ids[i+2]]);materials.push(mat.getName());}
  }
 }
 all[name]={vertices:verts,triangles:faces,materials};console.log(name,'window triangles',faces.length);
}
fs.writeFileSync(out,JSON.stringify(all));})().catch(e=>{console.error(e);process.exit(1)});

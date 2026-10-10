// Native blood / fragment emissions replayed against the workshop's flat floor.
const Emissions=Death.emissions, emissionRules=Emissions.rules;
const causeAudio=$('deathCauseAudio'),detachmentAudio=$('deathDetachAudio');
let deathSeed=1,deathSimulation=null,bloodTexture,lightningTextures=[],decalTextures=[];
const deathMask=()=>Emissions.masks.find(m=>m.id===$('deathRegion').value)?.mask||0;
const deathSfxProfile=()=>Emissions.sounds[$('deathCause').value]||Emissions.sounds.standard;
const detachmentPitch=()=>deathMask()===1?1.12:[8,16].includes(deathMask())?.92:1;
const deathExtraDuration=()=>Math.max(deathSfxProfile().death?.duration||0,deathMask()?(deathSfxProfile().dismemberment.duration/detachmentPitch()):0,deathMask()?emissionRules.fragment_seconds:0);
function audioLayers(){return [
 {audio:deathAudio,clip:deathCry(),enabled:$('deathSound').checked,gain:Number($('deathCryVolume').value),pitch:1},
 {audio:causeAudio,clip:deathSfxProfile().death,enabled:$('deathCauseSound').checked,gain:Number($('deathCauseVolume').value),pitch:1},
 {audio:detachmentAudio,clip:deathMask()?deathSfxProfile().dismemberment:null,enabled:$('deathDetachSound').checked,gain:Number($('deathDetachVolume').value),pitch:detachmentPitch()}
]}
function configureEmissionAudio(){
 const profile=deathSfxProfile();
 for(const [audio,c]of [[causeAudio,profile.death],[detachmentAudio,deathMask()?profile.dismemberment:null]]){
  if(c){audio.src=c.src;audio.load()}else{audio.removeAttribute('src');audio.load()}
 }
 causeAudio.hidden=!profile.death;detachmentAudio.hidden=!deathMask();
 $('deathCauseAudioNote').textContent=profile.death?'Son élémentaire utilisé par le jeu.':'Aucun son élémentaire pour une mort standard ou un état tactique.';
 $('deathDetachAudioNote').textContent=deathMask()?`Une salve d’arrachement · pitch ${Math.round(detachmentPitch()*100)} %`:'Choisir un membre détaché pour écouter ce son.';
 for(const layer of audioLayers()){layer.audio.volume=layer.gain;layer.audio.playbackRate=Number($('speed').value)*layer.pitch;layer.audio.preservesPitch=layer.audio!==detachmentAudio}
}
function syncAllDeathAudio(play=false){
 if(!scene?.death)return;
 for(const layer of audioLayers()){
  const {audio,clip:sample}=layer;if(!sample){audio.pause();continue}
  const at=Math.min(frame/clip.fps*layer.pitch,sample.duration);
  audio.volume=layer.gain;audio.playbackRate=Number($('speed').value)*layer.pitch;
  if(Math.abs(audio.currentTime-at)>.06)audio.currentTime=at;
  if(play&&layer.enabled&&layer.gain>0&&at<sample.duration-.01)audio.play().catch(e=>{if(e.name!=='AbortError')$('deathAudioStatus').textContent='Un son n’a pas démarré. Le lecteur individuel permet de le relancer.'});else audio.pause();
 }
}
function pauseAllDeathAudio(){for(const audio of [deathAudio,causeAudio,detachmentAudio])audio.pause()}
for(const m of Emissions.masks)$('deathRegion').add(new Option(m.name,m.id));
$('deathRegion').onchange=()=>{configureDeath();recenter()};
$('deathSprayVariant').onclick=()=>{++deathSeed;configureDeath();recenter()};
for(const id of ['deathBlood','deathDecals'])$(id).onchange=draw;
for(const id of ['deathSound','deathCauseSound','deathDetachSound','deathCryVolume','deathCauseVolume','deathDetachVolume'])$(id).oninput=$(id).onchange=()=>{syncAllDeathAudio(playing);draw()};
$('deathCryVolume').value=emissionRules.voice_volume;$('deathCauseVolume').value=emissionRules.death_volume;$('deathDetachVolume').value=emissionRules.dismember_volume;
$('speed').onchange=()=>{if(scene?.death)syncAllDeathAudio(playing)};

function prepareDeathSimulation(){
 const mask=deathMask();if(!mask){deathSimulation={fragments:[],particles:[],decals:[]};return}
 let seed=(deathSeed*2654435761+mask*97)>>>0;
 const random=(low,high)=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return low+(seed>>>0)/4294967296*(high-low)};
 const particles=[],pool=[],decals=[],fragments=[],r=emissionRules,dt=r.dt,profile=deathProfile(),layers=profile?Death.effects[profile.effect].layers:[];
 let cursor=0;
 function retain(p){const old=pool[cursor%r.capacity];if(old)old.until=Math.min(old.until,p.born);pool[cursor++%r.capacity]=p;particles.push(p)}
 function blood(f,time,burst){
  const spread=burst?r.burst_spread:r.trail_spread,duration=random(r.particle_min_seconds,r.particle_max_seconds);
  retain({born:time,until:time+duration,duration,origin:add(f.position,[random(-3,3),random(-3,3),random(-2,2)]),
   velocity:add(times(f.velocity,burst?.22:.10),[random(-spread,spread),random(-spread,spread),random(burst?20:2,burst?100:28)]),
   gravity:r.blood_gravity,blood:true,size:random(burst?.65:.35,burst?1.3:.75),color:[random(.55,.8),random(.015,.035),random(.02,.04)]});
 }
 function element(f,time,layer){
  const duration=random(r.particle_min_seconds,r.particle_max_seconds);
  retain({born:time,until:time+duration,duration,origin:add(f.position,[random(-2,2),random(-2,2),random(-2,2)]),
   velocity:add(times(f.velocity,.12),[random(-16,16),random(-16,16),random(0,18)]),
   gravity:layer.pattern==='Drops'?-125:['Rise','Cloud'].includes(layer.pattern)?22:-60,blood:false,
   texture:layer.texture,pattern:layer.pattern,size:layer.pattern==='Cloud'?3.2:layer.pattern==='Rings'?2:1.6,
   line:['Arcs','Sparks','Chain','Burst'].includes(layer.pattern),span:[random(-4,4),random(-4,4),random(-4,4)],color:layer.color.map(x=>x/255)});
 }
 function stain(f,time){decals.push({born:time,position:[f.position[0],f.position[1],.04],texture:Math.floor(random(0,6))})}
 for(const meta of Emissions.fragments){
  if(!(meta.region&mask))continue;
  const force=['kinetic','resonant_impact'].includes($('deathCause').value)?1.3:1;
  const f={...meta,position:add(Emissions.spawn_points[String(meta.region)],[random(-3,3),random(-3,3),0]),
   velocity:times([random(-130,130),random(-130,130),random(100,230)],force),
   angles:[random(-90,90),random(0,360),random(-90,90)],spin:[random(-350,350),random(-350,350),random(-350,350)],
   tracks:[],grounded:false,decalsLeft:r.impact_decal_budget,next:0};
  fragments.push(f);if(f.whole)for(let n=0;n<r.burst_count;n++)blood(f,0,true);
 }
 const steps=Math.ceil(r.fragment_seconds/dt);
 for(let step=0;step<=steps;step++){
  const time=step*dt;
  if(step)for(const f of fragments){
   if(f.grounded)continue;
   f.velocity[2]-=r.gravity*dt;f.position=add(f.position,times(f.velocity,dt));f.angles=add(f.angles,times(f.spin,dt));
   f.spin=f.spin.map(v=>Math.sign(v)*Math.max(0,Math.abs(v)-40*r.friction*dt));
   if(f.position[2]<r.floor_radius){
    f.position[2]=r.floor_radius;
    if(f.decalsLeft>0){stain(f,time);--f.decalsLeft}
    f.velocity[2]=Math.abs(f.velocity[2])*(1-r.friction);
    if(f.velocity[2]<r.gravity*dt||dot(f.velocity,f.velocity)<900){
     f.grounded=true;f.velocity=[0,0,0];f.spin=[0,0,0];f.angles=[f.rest_pitch,f.angles[1],0];
     if(f.whole)f.position[2]=f.floor_offset;
     stain(f,time);
    }
   }
  }
  let emitted=0;
  for(let j=0;j<fragments.length;j++){
   // Keep the native per-frame budget, rotating the scan to serve every piece.
   const f=fragments[(j+step)%fragments.length];
   if(time<=r.trail_seconds&&emitted<r.emission_limit&&time+1e-6>=f.next&&(Math.hypot(...f.velocity)>12||time<.15)){
    for(let n=0;n<(f.whole?2:1);n++)blood(f,time,false);
    for(const layer of layers)element(f,time,layer);
    f.next=time+r.trail_interval;++emitted;
   }
  }
  for(const f of fragments)f.tracks.push({position:f.position.slice(),angles:f.angles.slice()});
 }
 deathSimulation={fragments,particles,decals};
}
function fragmentPose(body,time=frame/clip.fps){
 const f=deathSimulation?.fragments.find(f=>f.body===body);if(!f)return null;
 const t=Math.min(f.tracks.length-1,time/emissionRules.dt),i=Math.floor(t),a=f.tracks[i],b=f.tracks[Math.min(i+1,f.tracks.length-1)],mix=t-i;
 return {position:a.position.map((v,k)=>v+(b.position[k]-v)*mix),angles:a.angles.map((v,k)=>v+(b.angles[k]-v)*mix)};
}
function fragmentMatrix(body){
 const p=fragmentPose(body),m=mul(rotate(2,p.angles[1]),mul(rotate(1,-p.angles[0]),rotate(0,p.angles[2])));
 for(let i=0;i<3;i++)m[12+i]=p.position[i];return new Float32Array(m);
}
function deathGroupVisible(g){
 if(!scene.death)return true;
 if(g.fragment!==undefined)return !!(g.region&deathMask())&&frame/clip.fps<emissionRules.fragment_seconds;
 if(g.region!==undefined)return g.wound?!!(g.region&deathMask()):!(g.region&deathMask());
 return true;
}
function emissionState(){
 const time=frame/clip.fps,active=(deathSimulation?.particles||[]).filter(p=>p.born<=time&&time<p.until);
 return {region:$('deathRegion').value,mask:deathMask(),seed:deathSeed,
  fragments:(deathSimulation?.fragments||[]).length*(time<emissionRules.fragment_seconds?1:0),
  blood:$('deathBlood').checked?active.filter(p=>p.blood).length:0,
  elemental:$('deathEffects').checked?active.filter(p=>!p.blood).length:0,retained:active.length,capacity:emissionRules.capacity,
  decals:$('deathDecals').checked?(deathSimulation?.decals||[]).filter(d=>d.born<=time).length:0,
  deathSample:deathSfxProfile().death?.path||null,detachSample:deathMask()?deathSfxProfile().dismemberment.path:null,
  pitch:detachmentPitch(),causeAudioTime:causeAudio.currentTime,detachmentAudioTime:detachmentAudio.currentTime,
  causeAudioPlaying:!causeAudio.paused,detachmentAudioPlaying:!detachmentAudio.paused};
}
function uploadDeathVertices(vertices,texture,mode=gl.TRIANGLES){
 if(!vertices.length)return;gl.bindTexture(gl.TEXTURE_2D,texture);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.DYNAMIC_DRAW);gl.drawArrays(mode,0,vertices.length/9);
}
function quadVertices(corners,color=[1,1,1,1]){
 const uv=[[0,0],[1,0],[1,1],[0,1]],vertices=[];for(const i of [0,1,2,0,2,3])vertices.push(...corners[i],...uv[i],...color);return vertices;
}
function drawDeathDecals(view,w,h){
 if(!deathSimulation||!$('deathDecals').checked)return;
 const time=frame/clip.fps;deathUniforms(view,w,h);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);
 for(const d of deathSimulation.decals){
  if(d.born>time)continue;const asset=Emissions.decals[d.texture],x=asset.width/2,y=asset.height/2,p=d.position;
  uploadDeathVertices(quadVertices([add(p,[-x,-y,0]),add(p,[x,-y,0]),add(p,[x,y,0]),add(p,[-x,y,0])]),decalTextures[d.texture]);
 }
 gl.depthMask(true);gl.disable(gl.BLEND);
}
function drawDeathEmissions(view,w,h,right,up){
 if(!deathSimulation)return;
 const time=frame/clip.fps,active=deathSimulation.particles.filter(p=>p.born<=time&&time<p.until);
 if(!active.length)return;
 deathUniforms(view,w,h);gl.enable(gl.BLEND);gl.depthMask(false);
 const verticesByTexture=Array.from({length:5},()=>[]),bloodVertices=[];
 for(const p of active){
  const age=time-p.born,life=age/p.duration,a=add(add(p.origin,times(p.velocity,age)),[0,0,.5*p.gravity*age*age]);
  if(p.blood){
   if(!$('deathBlood').checked)continue;const x=times(right,p.size),y=times(up,p.size*1.4);
   bloodVertices.push(...quadVertices([sub(sub(a,x),y),sub(add(a,x),y),add(add(a,x),y),add(sub(a,x),y)],[...p.color,(1-life)*.92]));
  }else{
   if(!$('deathEffects').checked)continue;
   const primitive={a,b:add(a,times(p.span,1-life)),size:p.size,alpha:(1-life)*.8,line:p.line};let primitives=[primitive];
   if(p.pattern==='Rings'){
    primitives=[];const size=2+life*7;
    for(let i=0;i<12;i++){const t=i*Math.PI*2/12,t2=(i+1)*Math.PI*2/12;primitives.push({a:add(a,add(times(right,Math.cos(t)*size),times(up,Math.sin(t)*size))),b:add(a,add(times(right,Math.cos(t2)*size),times(up,Math.sin(t2)*size))),size:.22,alpha:primitive.alpha,line:true})}
   }else if(p.line)primitive.size=.3;
   // Shards in retained trails use the native 1.7 aspect instead of 2.
   let vertices=deathVertices(primitives,[0,0,0],right,p.pattern==='Shards'?times(up,.85):up,{pattern:p.pattern,color:p.color.map(c=>c*255)});
   verticesByTexture[p.texture].push(...vertices);
  }
 }
 gl.blendFunc(gl.SRC_ALPHA,gl.ONE);
 for(let i=0;i<5;i++){const frames=deathSprites[i];uploadDeathVertices(verticesByTexture[i],frames[Math.floor(time*10)%frames.length])}
 gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);uploadDeathVertices(bloodVertices,bloodTexture);
 gl.depthMask(true);gl.disable(gl.BLEND);
}
async function emissionTexture(src){
 const im=new Image();im.src=src;await im.decode();const tex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,tex);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,im);
 for(const p of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_2D,p,gl.LINEAR);for(const p of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,p,gl.CLAMP_TO_EDGE);return tex;
}
async function initDeathEmissionTextures(){
 [bloodTexture,lightningTextures,decalTextures]=await Promise.all([emissionTexture(Emissions.blood_sprite[0]),Promise.all(Emissions.lightning_sprite.map(emissionTexture)),Promise.all(Emissions.decals.map(d=>emissionTexture(d.src)))]);
}

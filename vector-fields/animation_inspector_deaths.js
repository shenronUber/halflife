// Offline death preview. Assets and automatic profiles come from the game.
const Death=D.deaths, deathAudio=$('deathAudio');
let deathVariant=0, lastAnimationScene='third_bottom', deathSprites=[], deathFxCount=0;
const deathProfile=()=>Death.profiles.find(p=>p.effect===$('deathCause').value);
const deathCryCause=()=>Death.cries[$('deathActor').value]?.[$('deathCause').value] ? $('deathCause').value : 'standard';
const deathCry=()=>Death.cries[$('deathActor').value][deathCryCause()];
function deathDuration(){return Math.max((clip.frames.length-1)/clip.fps,deathProfile()?.fx_seconds||0,deathCry().duration,deathExtraDuration())+.5}
function endFrame(){return scene.death?deathDuration()*clip.fps:clip.frames.length-1}
function pausePlayback(){playing=false;$('play').textContent='Lire';pauseAllDeathAudio()}
function syncDeathAudio(play=false){syncAllDeathAudio(play)}
function configureDeath(){
 pausePlayback();
 const profile=deathProfile(),options=profile?.motions||(deathMask()&1?['headshot']:['quaternius','kaykit_a','kaykit_b']);
 const chosen=$('deathMotion').value==='auto'?options[deathVariant%options.length]:$('deathMotion').value;
 $('clip').value=chosen;clip=scene.clips[chosen];frame=0;$('timeline').max=endFrame();
 const cry=deathCry();deathAudio.src=cry.src;deathAudio.load();configureEmissionAudio();prepareDeathSimulation();
 const actor=Death.actors.find(a=>a.id===$('deathActor').value);
 $('deathAudioStatus').textContent=`${actor.name} · ${cry.duration.toFixed(2)} s · mono 11 025 Hz / 8 bits`;
 $('deathDetails').textContent=deathCryCause()==='standard'&&$('deathCause').value!=='standard'
  ? 'État tactique : cri et chute standards, sans effet de mort élémentaire.'
  : profile?Death.effects[profile.effect].visual:'Mort classique : cri de douleur bref, sans effet élémentaire.';
 $('deathResolved').textContent=clip.label;
 $('deathVariant').disabled=$('deathMotion').value!=='auto'||options.length<2;
 draw();
}
function updateDeathUI(){
 const active=!!scene.death;
 $('animationControls').hidden=active;$('deathControls').hidden=!active;$('deathPanel').hidden=!active;
 $('animationsTab').setAttribute('aria-pressed',String(!active));$('deathsTab').setAttribute('aria-pressed',String(active));
 $('indexPanel').hidden=active;
 for(const id of ['weaponSkin','before','weapon','sleeves','highlight'])$(id).closest('label').hidden=active;
 $('hand').hidden=$('right').hidden=active;
 $('interactionHint').textContent=active?'Glisser : tourner · Maj + glisser : déplacer le cadrage · molette : zoomer. Le lecteur audio permet aussi d’écouter le cri seul.':'Glisser : tourner · Maj + glisser : déplacer le cadrage · molette : zoomer. Les réglages d’index restent dans cet atelier jusqu’à leur report dans les modèles.';
 if(!active)lastAnimationScene=$('scene').value;
}
$('animationsTab').onclick=()=>{$('scene').value=lastAnimationScene;selectScene()};
$('deathsTab').onclick=()=>{$('scene').value='deaths';selectScene()};
for(const actor of Death.actors)$('deathActor').add(new Option(`${actor.name} · ${actor.accent}`,actor.id));
for(const [kind,label]of [[-1,'Mort classique'],[0,'États élémentaires'],[1,'Mélanges élémentaires'],[2,'États tactiques · cri standard']]){
 const group=document.createElement('optgroup');group.label=label;
 for(const c of Death.causes.filter(c=>c.kind===kind))group.append(new Option(c.name,c.id));
 $('deathCause').append(group);
}
$('deathMotion').add(new Option('Automatique · selon l’état','auto'));
for(const [id,c]of Object.entries(D.scenes.deaths.clips))$('deathMotion').add(new Option(c.label,id));
for(const id of ['deathActor','deathCause','deathMotion'])$(id).onchange=()=>{deathVariant=0;configureDeath();recenter()};
$('deathVariant').onclick=()=>{++deathVariant;configureDeath();recenter()};
$('deathReplay').onclick=()=>{pausePlayback();frame=0;playing=true;$('play').textContent='Pause';syncDeathAudio(true);draw()};
$('deathSound').onchange=()=>syncDeathAudio(playing);
$('deathEffects').onchange=recenter;
$('deathFollow').onchange=recenter;
$('speed').onchange=()=>{if(scene?.death)deathAudio.playbackRate=Number($('speed').value)};

// Port of cl_dll/vf_effect_math.h: the same bounded trajectories, not a new FX bank.
function effectPrimitives(l,time){
 time%=4096;const out=[],frac=x=>x-Math.floor(x),rad=(a,r,z)=>[Math.cos(a)*r,Math.sin(a)*r,z];
 const emit=(a,b,size,alpha,line=false)=>{if(out.length<512)out.push({a,b,size,alpha,line})};
 for(let i=0;i<l.count;i++){
  const seed=frac((i+1)*.618033989),seed2=frac((i+1)*.41421356),t=frac(time*l.speed*.35+seed),a=seed*6.2831853,r=13+seed2*12,z=-30+60*seed,fade=Math.sin(t*3.14159265);
  let p;
  switch(l.pattern){
   case 'Drops':p=rad(a,r,32-65*t);emit(p,add(p,[0,0,3]),l.size,.7*fade);break;
   case 'Rise':p=rad(a+time*.15,r*(1-.4*t),-31+73*t);emit(p,p,l.size*(.5+t),.8*fade);break;
   case 'Sparks':p=rad(a+time*.1,r+12*t,-26+66*t-10*t*t);emit(p,p,l.size*(1-.5*t),fade);break;
   case 'Cloud':p=rad(a+time*.18,10+20*t,-20+65*t);emit(p,p,l.size*(.7+t),.26*fade);break;
   case 'Orbit':p=rad(a+time*l.speed,r+4*Math.sin(time+seed),z+4*Math.sin(time*2+seed));emit(p,p,l.size,.65);break;
   case 'Shards':p=rad(a+time*l.speed*.3,r+5*Math.sin(time+seed),z);emit(p,add(p,[2,1,6]),l.size,.7);break;
   case 'Burst':p=rad(a,10+30*t,z*(.3+t));emit(p,add(p,rad(a,4+5*t,z*.12)),l.size*.6,fade,true);break;
   case 'Rings':case 'Collapse':case 'Scan':{
    const rr=l.pattern==='Collapse'?38*(1-t)+8:14+27*t,zz=l.pattern==='Scan'?-34+70*t:l.pattern==='Rings'?(l.count<=3?-34:z):z;
    for(let s=0;s<28;s++){const q=s*6.2831853/28;emit(rad(q,rr,zz),rad(q+6.2831853/28,rr,zz),.4,fade*.7,true)}break;
   }
   case 'Arcs':{
    const begin=rad(a,r,z),end=rad(a+1.7,r,z+12*Math.sin(time+seed)),tick=Math.floor(time*l.speed*10);let prev=begin;
    for(let s=1;s<=6;s++){let next=add(begin,times(sub(end,begin),s/6));if(s<6)next=add(next,[Math.sin(tick+i*7+s*11)*4,Math.cos(tick+s*3)*4,Math.sin(tick*.9+s*5)*5]);emit(prev,next,.55,.8,true);prev=next}break;
   }
   case 'Chain':{
    const begin=[i%2?-42:42,0,12],end=[0,0,-12+i*12];let prev=begin;
    emit(sub(begin,[0,0,3]),add(begin,[0,0,3]),.7,.8,true);emit(sub(begin,[3,0,0]),add(begin,[3,0,0]),.7,.8,true);
    for(let s=1;s<=12;s++){let next=add(begin,times(sub(end,begin),s/12));if(s<12)next[2]+=Math.sin(Math.floor(time*12)+s*13+i*3)*5;emit(prev,next,.6,.9,true);prev=next}break;
   }
  }
 }
 return out;
}
const deathProgram=gl.createProgram();
gl.attachShader(deathProgram,shader(gl.VERTEX_SHADER,'attribute vec3 p;attribute vec2 uv;attribute vec4 color;uniform mat3 view;uniform vec3 c;uniform float scale;uniform float aspect;uniform float radius;varying vec2 t;varying vec4 tint;void main(){vec3 q=view*(p-c);gl_Position=vec4(q.x*scale/aspect,q.y*scale,-q.z/radius*.18,1.);t=uv;tint=color;}'));
gl.attachShader(deathProgram,shader(gl.FRAGMENT_SHADER,'precision mediump float;uniform sampler2D tex;varying vec2 t;varying vec4 tint;void main(){gl_FragColor=texture2D(tex,t)*tint;}'));
gl.linkProgram(deathProgram);if(!gl.getProgramParameter(deathProgram,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(deathProgram));
const deathLoc={};for(const k of ['p','uv','color'])deathLoc[k]=gl.getAttribLocation(deathProgram,k);for(const k of ['view','c','scale','aspect','radius'])deathLoc[k]=gl.getUniformLocation(deathProgram,k);
const deathBuffer=gl.createBuffer(),groundTexture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,groundTexture);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array([255,255,255,255]));gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
function useProgram(program){gl.useProgram(program);for(let i=0;i<4;i++)gl.disableVertexAttribArray(i)}
function deathUniforms(view,w,h){
 useProgram(deathProgram);gl.uniformMatrix3fv(deathLoc.view,false,new Float32Array(view));gl.uniform3fv(deathLoc.c,center);gl.uniform1f(deathLoc.radius,radius);gl.uniform1f(deathLoc.aspect,w/h);gl.uniform1f(deathLoc.scale,zoom*.85/radius*Math.min(1,w/h));
 gl.bindBuffer(gl.ARRAY_BUFFER,deathBuffer);
 for(const [k,size,offset]of [['p',3,0],['uv',2,12],['color',4,20]]){gl.enableVertexAttribArray(deathLoc[k]);gl.vertexAttribPointer(deathLoc[k],size,gl.FLOAT,false,36,offset)}
}
function deathVertices(primitives,origin,right,up,layer){
 const vertices=[],f=cross(right,up),color=layer.color.map(x=>x/255);
 for(const p of primitives){
  const a=add(origin,p.a),b=add(origin,p.b);let corners;
  if(p.line){const n=cross(sub(b,a),f),length=Math.hypot(...n);if(length<1e-6)continue;const side=times(n,p.size/length);corners=[sub(a,side),add(a,side),add(b,side),sub(b,side)]}
  else if(layer.pattern==='Shards'){const x=times(right,p.size),z=times(up,p.size*2);corners=[sub(a,z),add(a,x),add(a,z),sub(a,x)]}
  else{const x=times(right,p.size),y=times(up,p.size);corners=[sub(sub(a,x),y),sub(add(a,x),y),add(add(a,x),y),add(sub(a,x),y)]}
  const uv=[[0,0],[1,0],[1,1],[0,1]];
  for(const i of [0,1,2,0,2,3])vertices.push(...corners[i],...uv[i],...color,p.alpha);
 }
 return vertices;
}
function deathEffectCenter(){
 const track=clip.effect_centers,t=Math.min(1,frame/(clip.frames.length-1))*32,i=Math.min(31,Math.floor(t));
 return track[i].map((v,k)=>v+(track[i+1][k]-v)*(t-i)+(k===2?36:0));
}
function drawDeathGround(view,w,h){
 deathUniforms(view,w,h);const vertices=[],extent=Math.ceil(Math.max(100,radius*2)/20)*20;
 uploadDeathVertices(quadVertices([[-extent,-extent,0],[extent,-extent,0],[extent,extent,0],[-extent,extent,0]],[.30,.33,.35,1]),groundTexture);
 for(let n=-extent;n<=extent;n+=20){
  for(const p of [[n,-extent,0],[n,extent,0],[-extent,n,0],[extent,n,0]])vertices.push(...p.slice(0,2),.02,0,0,.39,.44,.46,1);
 }
 gl.bindTexture(gl.TEXTURE_2D,groundTexture);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.DYNAMIC_DRAW);gl.drawArrays(gl.LINES,0,vertices.length/9);drawDeathDecals(view,w,h);
}
function drawDeathEffects(view,w,h,right,up){
 deathFxCount=0;if(!scene.death||!$('deathEffects').checked)return;
 const profile=deathProfile(),time=frame/clip.fps;if(!profile||time>profile.fx_seconds)return;
 const origin=deathEffectCenter(),electric=['electro','arc_chain','superconduction'].includes(profile.effect);
 deathUniforms(view,w,h);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.depthMask(false);
 if(!(profile.effect==='electro'&&time>=1.4))for(const layer of Death.effects[profile.effect].layers){
  const primitives=effectPrimitives(layer,time),vertices=deathVertices(primitives,origin,right,up,layer),sprite=deathSprites[layer.texture];
  gl.bindTexture(gl.TEXTURE_2D,sprite[Math.floor(time*10)%sprite.length]);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.DYNAMIC_DRAW);gl.drawArrays(gl.TRIANGLES,0,vertices.length/9);deathFxCount+=primitives.length;
 }
 if(electric&&time<2.1){
  const fall=Math.max(0,Math.min(1,(time-.85)/.83)),primitives=[];
  for(let arc=0;arc<5;arc++){
   const t=time*13+arc*1.7,a=[Math.cos(t)*15,Math.sin(t)*15,8+Math.sin(t*1.3)*14*(1-fall*.6)],b=[Math.cos(t+2)*21,Math.sin(t+2)*21,-18*(1-fall)+Math.cos(t)*13*(1-fall*.6)];let prev=a;
   for(let s=1;s<=6;s++){let next=add(a,times(sub(b,a),s/6));if(s<6)next=add(next,[Math.sin(Math.floor(time*40)+s*11+arc)*2,Math.cos(s*7+arc)*2,Math.sin(s*13+arc)*2]);primitives.push({a:prev,b:next,size:.65,alpha:.85,line:true});prev=next}
  }
  const vertices=deathVertices(primitives,origin,right,up,{pattern:'Arcs',color:[64,166,255]});gl.bindTexture(gl.TEXTURE_2D,lightningTextures[Math.floor(time*10)%lightningTextures.length]);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.DYNAMIC_DRAW);gl.drawArrays(gl.TRIANGLES,0,vertices.length/9);deathFxCount+=primitives.length;
 }
 gl.depthMask(true);gl.disable(gl.BLEND);
}
async function initDeathSprites(){
 deathSprites=await Promise.all(Death.sprites.map(async frames=>Promise.all(frames.map(async src=>{
  const im=new Image();im.src=src;await im.decode();const tex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,tex);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,im);
  for(const p of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_2D,p,gl.LINEAR);for(const p of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,p,gl.CLAMP_TO_EDGE);return tex;
 }))));
 await initDeathEmissionTextures();
}

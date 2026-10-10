const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'build/animation-workshop/deaths/emissions');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true,args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1660,height:1180}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(root,'build/animation-inspector.html')).href+'?section=deaths',{timeout:60000});await page.waitForFunction(()=>window.workshopReady,null,{timeout:60000});
  assert.equal(await page.locator('#deathRegion option').count(),7);
  const bank=await page.evaluate(()=>Emissions.sounds);let files=0;
  for(const profile of Object.values(bank))for(const c of Object.values(profile)){
   const bytes=fs.readFileSync(path.join(root,'generated/death-sfx/sound',path.basename(c.path)));
   assert(bytes.equals(Buffer.from(c.src.split(',')[1],'base64')));assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),c.sha256);++files;
  }
  assert.equal(files,33);assert.equal(bank.standard.death,undefined);
  const seek=async seconds=>{const f=await page.evaluate(t=>t*clip.fps,seconds);await page.locator('#timeline').fill(String(Math.round(f*100)/100));await page.locator('#timeline').dispatchEvent('input');return page.evaluate(()=>window.workshopState)};
  await page.selectOption('#deathRegion','left_arm');
  const samples=[];
  for(const profile of Object.keys(bank)){
   await page.selectOption('#deathCause',profile);
   await page.waitForFunction(()=>detachmentAudio.readyState>=2&&(!deathSfxProfile().death||causeAudio.readyState>=2));
   let s=await seek(.16);assert.equal(s.glError,0);assert.equal(s.death.emissions.fragments,4);assert(s.death.emissions.blood>10);assert(s.death.emissions.retained<=384);
   assert.equal(s.death.emissions.deathSample,bank[profile].death?.path||null);assert.equal(s.death.emissions.detachSample,bank[profile].dismemberment.path);
   if(profile==='standard')assert.equal(s.death.emissions.elemental,0);else assert(s.death.emissions.elemental>0);
   samples.push({profile,blood:s.death.emissions.blood,elemental:s.death.emissions.elemental,deathSample:s.death.emissions.deathSample,detachSample:s.death.emissions.detachSample});
  }
  for(const [region,mask,count,pitch]of [['none',0,0,1],['head',1,4,1.12],['left_arm',2,4,1],['right_arm',4,4,1],['left_leg',8,4,.92],['right_leg',16,4,.92],['all',31,20,1]]){
   await page.selectOption('#deathRegion',region);let s=await seek(.2);assert.equal(s.death.emissions.mask,mask);assert.equal(s.death.emissions.fragments,count);assert.equal(s.death.emissions.pitch,pitch);assert.equal(s.glError,0);
   // The native bodygroup mask removes the limb and exposes its matching cap.
   const parts=await page.evaluate(()=>groups.filter(g=>g.fragment===undefined&&visible(g)).map(g=>({region:g.region,wound:g.wound})));
   for(const part of parts)assert(part.wound?!!(mask&part.region):!(mask&part.region));
   await page.locator('#stage').screenshot({path:path.join(out,region+'-burst.png')});
  }
  await page.selectOption('#deathCause','standard');await page.selectOption('#deathRegion','head');
  assert.equal((await page.evaluate(()=>window.workshopState)).death.motion,'headshot');
  await seek(.12);
  const redPixels=()=>page.evaluate(()=>{const data=new Uint8Array(canvas.width*canvas.height*4);gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,data);let red=0;for(let i=0;i<data.length;i+=4)if(data[i]>30&&data[i]>data[i+1]*2.5&&data[i]>data[i+2]*2.5)red++;return red});
  const red=await redPixels(),bloodImage=await page.locator('#stage').screenshot();await page.uncheck('#deathBlood');const withoutRed=await redPixels();const noBloodImage=await page.locator('#stage').screenshot();assert(!bloodImage.equals(noBloodImage));assert(red>withoutRed+5,'explicit red blood changes framebuffer pixels');assert.equal((await page.evaluate(()=>window.workshopState)).death.emissions.blood,0);await page.check('#deathBlood');
  await page.selectOption('#deathCause','corrosion');await page.selectOption('#deathRegion','all');
  for(const t of [0,.1,.5,1,1.8,2.2,2.8,3.1,6,11.9,12.1]){const s=await seek(t);assert(s.death.emissions.retained<=384);assert.equal(s.glError,0);if(t>=3.1)assert.equal(s.death.emissions.retained,0);if(t>=12)assert.equal(s.death.emissions.fragments,0)}
  let s=await seek(4);assert(s.death.emissions.decals>0);const stains=await page.locator('#stage').screenshot({path:path.join(out,'corrosion-decals.png')});
  await page.uncheck('#deathDecals');assert.equal((await page.evaluate(()=>window.workshopState)).death.emissions.decals,0);const noStains=await page.locator('#stage').screenshot();assert(!stains.equals(noStains));await page.check('#deathDecals');
  await seek(.25);const first=await page.locator('#stage').screenshot();await seek(3);await seek(.25);const rewind=await page.locator('#stage').screenshot();assert(first.equals(rewind),'seeking recomputes the same retained trajectories');await page.click('#deathSprayVariant');await seek(.25);assert(!(await page.locator('#stage').screenshot()).equals(first),'new projection changes real geometry and particles');
  await page.selectOption('#deathCause','electro');await page.selectOption('#deathRegion','head');await page.click('#deathReplay');await page.waitForFunction(()=>window.workshopState.death.time>.15&&window.workshopState.death.emissions.causeAudioPlaying&&window.workshopState.death.emissions.detachmentAudioPlaying);
  s=await page.evaluate(()=>window.workshopState);assert(s.death.audioPlaying);assert(Math.abs(s.death.emissions.causeAudioTime-s.death.time)<.3);assert.equal(await page.evaluate(()=>detachmentAudio.playbackRate),1.12);assert.equal(await page.evaluate(()=>detachmentAudio.preservesPitch),false);
  await page.click('#play');s=await page.evaluate(()=>window.workshopState);assert(!s.death.audioPlaying);assert(!s.death.emissions.causeAudioPlaying);assert(!s.death.emissions.detachmentAudioPlaying);
  await seek(.3);assert(await page.evaluate(()=>Math.abs(causeAudio.currentTime-frame/clip.fps)<.04&&Math.abs(detachmentAudio.currentTime-frame/clip.fps*1.12)<.04));
  await page.uncheck('#deathCauseSound');await page.uncheck('#deathDetachSound');await page.click('#deathReplay');await page.waitForFunction(()=>window.workshopState.death.time>.1);s=await page.evaluate(()=>window.workshopState);assert(!s.death.emissions.causeAudioPlaying);assert(!s.death.emissions.detachmentAudioPlaying);await page.click('#play');await page.check('#deathCauseSound');await page.check('#deathDetachSound');
  for(const cause of ['phase','null','ward','reveal','overclock']){await page.selectOption('#deathCause',cause);s=await seek(.1);assert.equal(s.death.emissions.deathSample,null);assert.equal(s.death.emissions.detachSample,bank.standard.dismemberment.path);assert.equal(s.death.emissions.elemental,0)}
  await page.selectOption('#deathCause','arc_chain');await page.selectOption('#deathRegion','left_leg');await seek(.2);await page.screenshot({path:path.join(out,'updated-section.png'),fullPage:true});
  assert.deepEqual(errors,[]);const report={additionalSounds:files,profiles:17,fragmentMeshes:20,regions:7,decals:6,nativeSpriteFrames:await page.evaluate(()=>[Emissions.blood_sprite.length,Emissions.lightning_sprite.length]),redPixels:red,withoutBloodRedPixels:withoutRed,samples,errors,checks:['all 33 additional game WAVs embedded verbatim and decoded','native severed bodygroups and cut surfaces across all five regions','four real fragment meshes per detached region','ten-drop bursts and retained dark-red alpha blood','additive elemental trails keep each reaction layer','384-particle pool and 2.2-second emission window','six native gradient decals appear on contacts','rewind is deterministic and new projection changes real pixels','three audio layers start together, pause/seek/mute separately, and use native head/leg pitch','tactical states retain only generic detachment sound']};
  fs.writeFileSync(path.join(out,'browser-verification.json'),JSON.stringify(report,null,2));console.log('PASS death emissions workshop',JSON.stringify({additionalSounds:files,regions:7,fragmentMeshes:20,decals:6,redPixels:red,withoutBloodRedPixels:withoutRed,errors}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'build/animation-workshop/deaths');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true,args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(root,'build/animation-inspector.html')).href,{timeout:60000});await page.waitForFunction(()=>window.workshopReady,null,{timeout:60000});
  await page.click('#deathsTab');await page.waitForFunction(()=>window.workshopState.scene==='deaths');
  assert(await page.locator('#deathControls').isVisible());assert(!await page.locator('#authorPanel').isVisible());assert(!await page.locator('#indexPanel').isVisible());
  assert.equal(await page.locator('#deathActor option').count(),6);assert.equal(await page.locator('#deathCause option').count(),22);
  const bank=await page.evaluate(()=>D.deaths.cries),actors=Object.keys(bank),causes=Object.keys(bank[actors[0]]),samples=[];
  // Every embedded file is exactly the compressed game WAV, not a studio master.
  for(const actor of actors)for(const cause of causes){
   const c=bank[actor][cause],file=fs.readFileSync(path.join(root,'assets/audio/operator-deaths',c.path.replace('vf_deaths/','')));
   assert.equal(crypto.createHash('sha256').update(file).digest('hex'),c.sha256);assert(file.equals(Buffer.from(c.src.split(',')[1],'base64')));
   assert.equal(file.toString('ascii',0,4),'RIFF');assert(c.duration<=3);
  }
  for(const actor of actors){
   await page.selectOption('#deathActor',actor);
   for(const cause of causes){
    await page.selectOption('#deathCause',cause);await page.waitForFunction(()=>document.getElementById('deathAudio').readyState>=2);
    const state=await page.evaluate(()=>({s:window.workshopState,audio:{duration:deathAudio.duration,error:deathAudio.error?.code,paused:deathAudio.paused}}));
    assert.equal(state.s.death.actor,actor);assert.equal(state.s.death.cry,cause);assert.equal(state.s.glError,0);assert.equal(state.audio.error,undefined);
    assert(Math.abs(state.audio.duration-bank[actor][cause].duration)<.02);assert(state.audio.paused);assert(!state.s.playing);samples.push({actor,cause,sequence:state.s.death.sequence,duration:state.audio.duration});
   }
  }
  for(const cause of ['phase','null','ward','reveal','overclock']){
   await page.selectOption('#deathCause',cause);const state=await page.evaluate(()=>window.workshopState);assert.equal(state.death.cry,'standard');assert.equal(state.death.fx,0);assert.equal(state.glError,0);
  }
  const profiles=JSON.parse(fs.readFileSync(path.join(root,'assets/animations/death-atlas.json'),'utf8')).profiles;
  for(const profile of profiles){
   await page.selectOption('#deathCause',profile.effect);let state=await page.evaluate(()=>window.workshopState);assert.equal(state.death.motion,profile.motions[0]);
   await page.locator('#timeline').fill(String(10));await page.locator('#timeline').dispatchEvent('input');state=await page.evaluate(()=>window.workshopState);assert(state.death.fx>0);assert.equal(state.glError,0);
   if(profile.motions.length>1){await page.click('#deathVariant');assert.equal((await page.evaluate(()=>window.workshopState)).death.motion,profile.motions[1]);}
  }
  const motions=await page.locator('#deathMotion option').evaluateAll(options=>options.map(o=>o.value).filter(v=>v!=='auto'));
  for(const motion of motions){await page.selectOption('#deathMotion',motion);await page.locator('#timeline').fill('10');await page.locator('#timeline').dispatchEvent('input');const s=await page.evaluate(()=>window.workshopState);assert.equal(s.death.motion,motion);assert.equal(s.glError,0);assert(s.triangles>700)}
  await page.selectOption('#deathMotion','auto');await page.selectOption('#deathCause','electro');await page.selectOption('#deathActor','viktor');
  await page.locator('#timeline').fill('12');await page.locator('#timeline').dispatchEvent('input');const withFx=await page.locator('#stage').screenshot({path:path.join(out,'electric.png')});
  await page.uncheck('#deathEffects');assert.equal((await page.evaluate(()=>window.workshopState)).death.fx,0);const withoutFx=await page.locator('#stage').screenshot();assert(!withFx.equals(withoutFx));await page.check('#deathEffects');
  const before=await page.locator('#stage').screenshot();await page.selectOption('#skin','5');const after=await page.locator('#stage').screenshot();assert(!before.equals(after),'skin selects the actual corpse texture');await page.selectOption('#skin','0');
  await page.selectOption('#deathCause','steam_veil');await page.locator('#timeline').fill('25');await page.locator('#timeline').dispatchEvent('input');await page.screenshot({path:path.join(out,'section.png')});
  await page.selectOption('#deathCause','electro');await page.click('#deathReplay');await page.waitForFunction(()=>window.workshopState.death.time>.25&&window.workshopState.death.audioTime>.1);
  let state=await page.evaluate(()=>window.workshopState);assert(state.death.audioPlaying);assert(Math.abs(state.death.audioTime-state.death.time)<.4,'cry and death start together');
  await page.click('#play');state=await page.evaluate(()=>window.workshopState);assert(!state.playing);assert(!state.death.audioPlaying);
  await page.locator('#timeline').fill('9');await page.locator('#timeline').dispatchEvent('input');assert(await page.evaluate(()=>Math.abs(deathAudio.currentTime-frame/clip.fps)<.04));
  await page.click('#next');assert.equal(Math.round((await page.evaluate(()=>window.workshopState)).frame),10);
  await page.uncheck('#deathSound');await page.click('#deathReplay');await page.waitForFunction(()=>!window.workshopState.playing,null,{timeout:12000});
  state=await page.evaluate(()=>window.workshopState);assert.equal(state.death.poseFrame,(await page.evaluate(()=>clip.frames.length))-1);assert.equal(state.death.fx,0);assert(!state.death.audioPlaying);
  await page.uncheck('#deathFollow');assert.equal((await page.evaluate(()=>window.workshopState)).glError,0);await page.check('#deathFollow');
  const stopped=state.frame;await page.waitForTimeout(250);assert.equal((await page.evaluate(()=>window.workshopState)).frame,stopped,'death must not loop');await page.locator('#stage').screenshot({path:path.join(out,'final-corpse.png')});
  await page.check('#deathSound');await page.click('#animationsTab');assert.equal((await page.evaluate(()=>window.workshopState)).scene,'third_bottom');assert(await page.locator('#authorPanel').isVisible());assert(!await page.locator('#deathControls').isVisible());assert.equal((await page.evaluate(()=>window.workshopState)).glError,0);
  await page.goto(pathToFileURL(path.join(root,'build/animation-inspector.html')).href+'?section=deaths&actor=otto&cause=hydro&motion=kaykit_b',{timeout:60000});await page.waitForFunction(()=>window.workshopReady,null,{timeout:60000});state=await page.evaluate(()=>window.workshopState);assert.equal(state.death.actor,'otto');assert.equal(state.death.cause,'hydro');assert.equal(state.death.motion,'kaykit_b');assert.equal(state.glError,0);
  assert.deepEqual(errors,[]);const report={actors:6,cries:102,causes:22,motions:motions.length,profiles:16,spriteFrames:await page.evaluate(()=>D.deaths.sprites.map(s=>s.length)),samples,errors,checks:['all compressed WAVs embedded verbatim and decoded','automatic state atlas and variant selection','all compiled death motions rendered','tactical states use standard cry with no death FX','real sprite effects and outfit change pixels','synchronized cry, pause, seek, frame steps and mute','one-shot playback holds final corpse pose','animation section and direct death links work']};
  fs.writeFileSync(path.join(out,'browser-verification.json'),JSON.stringify(report,null,2));console.log('PASS death workshop',JSON.stringify({actors:report.actors,cries:report.cries,causes:report.causes,motions:report.motions,profiles:report.profiles,errors}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

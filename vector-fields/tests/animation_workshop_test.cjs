const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'build/animation-workshop');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({channel:"msedge",headless:true,args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
 const page=await browser.newPage({viewport:{width:1500,height:1050}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(root,'build/animation-inspector.html')).href);await page.waitForFunction(()=>window.workshopReady,{timeout:30000});
 const samples=[];
 for(const scene of ['bottom','side','top','third_current','third_cs']){
  await page.selectOption('#scene',scene);await page.selectOption('#clip',scene==='third_current'?'shoot':'reload');
  await page.locator('#timeline').fill(scene==='third_current'?'2':scene==='third_cs'?'22':'34');
  await page.locator('#stage').screenshot({path:path.join(out,scene+'.png')});
  if(!scene.startsWith('third')){await page.click('#hand');await page.locator('#stage').screenshot({path:path.join(out,scene+'-hand.png')});}
  if(!scene.startsWith('third')){
   for(const underbarrel of ['0','1','2','3']){await page.selectOption('#underbarrel',underbarrel);const state=await page.evaluate(()=>window.workshopState);assert.equal(state.foregrip,underbarrel==='0');assert.equal(state.glError,0);}
   await page.selectOption('#underbarrel','0');await page.locator('#timeline').fill('34');
   const after=await page.locator('#stage').screenshot();
   await page.check('#before');await page.locator('#timeline').fill('34');
   const before=await page.locator('#stage').screenshot();assert(!after.equals(before),'grip comparison must change the rendered image');await page.uncheck('#before');
   for(const mag of ['0','1','2','3']){await page.selectOption('#mag',mag);await page.locator('#timeline').fill('83');assert.equal((await page.evaluate(()=>window.workshopState)).glError,0);}
   if(scene==='top')await page.locator('#stage').screenshot({path:path.join(out,'top-drum-insertion.png')});
   await page.selectOption('#mag','0');await page.locator('#timeline').fill('34');
  }
  const sample=await page.evaluate(()=>window.workshopState);assert.equal(sample.glError,0);assert(sample.triangles>700);samples.push(sample);
 }
 for(const scene of ['third_bottom','third_side','third_top']){
  await page.selectOption('#scene',scene);await page.selectOption('#clip','aim');await page.selectOption('#gait','walk');await page.locator('#timeline').fill('15');
  const before=await page.locator('#stage').screenshot();await page.locator('#gunZ').fill('0.5');await page.locator('#gunZ').dispatchEvent('input');
  const after=await page.locator('#stage').screenshot();assert(!after.equals(before),'authoring must move the actual mesh');assert.match(await page.locator('#ikStatus').textContent(),/Essai valide/);
  const downloaded=page.waitForEvent('download');await page.click('#saveRecipe');const download=await downloaded;await download.saveAs(path.join(out,scene+'-recipe.json'));const recipe=JSON.parse(fs.readFileSync(path.join(out,scene+'-recipe.json'),'utf8'));assert.equal(recipe.weapon.position[2],16.5);
  await page.click('#resetRecipe');await page.selectOption('#gait','none');await page.click('#full');
  for(const clip of ['aim','shoot','reload','rifle','crouch_aim','crouch_reload']){await page.selectOption('#clip',clip);await page.locator('#timeline').fill(clip==='shoot'?'1':'15');assert.equal((await page.evaluate(()=>window.workshopState)).glError,0)}
  await page.selectOption('#clip','aim');for(const gait of ['walk','run','crouch']){await page.selectOption('#gait',gait);await page.locator('#timeline').fill('18');assert.equal((await page.evaluate(()=>window.workshopState)).glError,0)}
  await page.selectOption('#gait','none');await page.locator('#timeline').fill('0');await page.locator('#stage').screenshot({path:path.join(out,scene+'-hold.png')});
  await page.selectOption('#clip','reload');await page.locator('#timeline').fill('20');await page.locator('#stage').screenshot({path:path.join(out,scene+'-reload.png')});samples.push(await page.evaluate(()=>window.workshopState));
 }
 await page.selectOption('#scene','side');await page.click('#play');await page.waitForFunction(()=>window.workshopState.frame>10);await page.click('#play');
 assert.equal((await page.evaluate(()=>window.workshopState)).glError,0);
 if(process.argv.includes('--media')){
  await page.setViewportSize({width:1100,height:1000});await page.selectOption('#scene','third_bottom');await page.selectOption('#clip','reload');
  for(let i=0;i<16;i++){await page.locator('#timeline').fill(String(i*3));await page.locator('#stage').screenshot({path:path.join(out,'reload-'+String(i).padStart(2,'0')+'.png')});}
  for(const scene of ['bottom','side','top']){
   await page.selectOption('#scene',scene);await page.selectOption('#underbarrel','0');await page.selectOption('#clip','reload');await page.click('#full');
   for(const f of [0,12,18,34,64,83,99,114,129,139]){await page.locator('#timeline').fill(String(f));await page.locator('#stage').screenshot({path:path.join(out,'foregrip-'+scene+'-'+String(f).padStart(3,'0')+'.png')});}
   await page.selectOption('#clip','aim');await page.click('#hand');await page.click('#reverse');await page.locator('#stage').screenshot({path:path.join(out,'foregrip-'+scene+'-contact.png')});
   await page.click('#sideview');await page.locator('#stage').screenshot({path:path.join(out,'foregrip-'+scene+'-contact-side.png')});await page.click('#reverse');await page.locator('#stage').screenshot({path:path.join(out,'foregrip-'+scene+'-contact-back.png')});
  }
 }
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'browser-verification.json'),JSON.stringify({samples,errors,checks:['all eight scenes rendered with WebGL','foregrip pose only for the angled grip; three other accessories keep standard support','R01 holds/reloads plus native gait layering rendered on three feeds','arm editor changes actual pixels and exports a reusable recipe','compiled animation timeline scrubbed','index closeups on all three feeds','continuous playback advances','before/after changes actual rendered pixels','all four magazines on all three feeds during insertion']},null,2));console.log('PASS animation workshop',JSON.stringify(samples));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

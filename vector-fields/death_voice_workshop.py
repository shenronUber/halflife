"""Build the integrated contextual nonverbal death voice bank and C++ catalog."""
from __future__ import annotations
import argparse,array,hashlib,html,json,re,shutil,subprocess,urllib.error,urllib.request,uuid,wave,zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import audio_workshop as audio
import voice_workshop as voices
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/death_voices.json'
ASSETS=ROOT/'assets/audio/operator-deaths'

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def catalog():
 d=read(DATA);effects=read(ROOT/'data/effects.json')['effects'];active=read(ROOT/'data/voices.json')['actors']
 assert [a['id'] for a in d['actors']]==[a['id'] for a in active]
 assert len(d['actors'])==6 and len(d['causes'])==17
 assert d['max_duration_seconds']==3 and 1<=d['max_vocalizations']<=2
 assert isinstance(d['asset_version'],int) and d['asset_version']>=2
 assert {c['id'] for c in d['causes']}=={'standard'}|{e['id'] for e in effects if e['kind']<2}
 assert d['tactical_fallback']=={e['id']:'standard' for e in effects if e['kind']==2}
 for a in d['actors']:
  assert set(a.get('script_overrides',{}))<={c['id'] for c in d['causes']}
 for c in d['causes']+ [{'id':a['id']+'/'+k,'text':v} for a in d['actors'] for k,v in a.get('script_overrides',{}).items()]:
  script=re.sub(r'\[[^\]]+\]','',c['text'])
  assert not re.search(r'[^A-Za-z!?. \n-]',script),c['id']
  assert all(re.fullmatch(r'[AaEeGgHhKkMmNnOoRrUuWw]+',s) for s in re.findall(r'[A-Za-z]+',script)),c['id']
  assert 1<=len(re.findall(r'[A-Za-z][A-Za-z-]*',script))<=d['max_vocalizations'],c['id']
 return d

def items():
 for a in catalog()['actors']:
  for c in catalog()['causes']:
   effective=dict(c);effective['text']=a.get('script_overrides',{}).get(c['id'],c['text']);yield a,effective

def stem(a,c):
 folder=ASSETS/a['id'];folder.mkdir(parents=True,exist_ok=True)
 return folder/(c['id']+'_v'+str(catalog()['asset_version']))

def generate(limit):
 key=audio.load_key();quota=audio.status(key)
 if quota.get('character_limit') and quota.get('character_count',0)>=quota['character_limit']:raise RuntimeError('Included quota exhausted.')
 jobs=[(a,c) for a,c in items() if not stem(a,c).with_suffix('.json').exists()][:limit]
 def one(job):
  a,c=job;s=stem(a,c);voice=read((DATA.parent/a['voice_reference']).resolve())['response']['voice_id']
  body={'text':c['text'],'model_id':'eleven_v4','voice_settings':{'stability':.5,'similarity_boost':.85}}
  pending=s.with_suffix('.pending')
  if pending.exists():raise RuntimeError('Uncertain provider outcome: '+str(pending))
  audio.json_write(pending,{'voice_id':voice,'request_sha256':voices.signature(body)})
  try:raw,headers=audio.api('/v1/text-to-speech/'+voice+'?output_format=mp3_44100_128',key,body)
  except RuntimeError as error:
   if str(error).startswith('ElevenLabs HTTP 4'):pending.unlink()
   raise
  if len(raw)<128 or not(raw[:3]==b'ID3' or(raw[0]==255 and raw[1]&224==224)):raise RuntimeError('Invalid MP3; pending marker retained.')
  mp3=s.with_suffix('.mp3');mp3.write_bytes(raw)
  dry=s.with_name(s.name+'_source_master.wav')
  if not audio.convert(mp3,dry):raise RuntimeError('ffmpeg required.')
  audio.json_write(s.with_suffix('.json'),{'provider':'ElevenLabs','voice_id':voice,'actor':a['id'],'cause':c['id'],'text':c['text'],'request':body,'request_sha256':voices.signature(body),'sha256':sha(mp3),'request_id':headers.get('request-id') or headers.get('Request-Id')})
  pending.unlink();print('SAVED',a['id'],c['id'],flush=True)
 with ThreadPoolExecutor(max_workers=2) as pool:
  for _ in pool.map(one,jobs):pass
 audio.status(key)

def speech_check(limit):
 key=audio.load_key()
 jobs=[(a,c) for a,c in items() if stem(a,c).with_suffix('.json').exists() and not stem(a,c).with_name(stem(a,c).name+'_asr.json').exists()][:limit]
 def one(job):
  a,c=job;s=stem(a,c);dry=s.with_name(s.name+'_source_master.wav');target=s.with_name(s.name+'_asr.json');pending=target.with_suffix('.pending')
  if pending.exists():raise RuntimeError('Uncertain earlier transcription: '+str(pending))
  audio.json_write(pending,{'model_id':'scribe_v2','sha256':sha(dry)})
  boundary='VFDeath'+uuid.uuid4().hex;parts=[]
  for name,value in [('model_id','scribe_v2'),('tag_audio_events','true'),('language_code','en')]:parts.append(('--'+boundary+'\r\nContent-Disposition: form-data; name="'+name+'"\r\n\r\n'+value+'\r\n').encode())
  parts.append(('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="death.wav"\r\nContent-Type: audio/wav\r\n\r\n').encode()+dry.read_bytes()+b'\r\n')
  parts.append(('--'+boundary+'--\r\n').encode())
  req=urllib.request.Request(audio.BASE_URL+'/v1/speech-to-text',data=b''.join(parts),headers={'xi-api-key':key,'Content-Type':'multipart/form-data; boundary='+boundary,'Accept':'application/json'})
  try:
   with urllib.request.urlopen(req,timeout=180) as response:result=json.loads(response.read())
  except urllib.error.HTTPError as error:
   if 400<=error.code<500:pending.unlink()
   raise RuntimeError('ElevenLabs transcription HTTP '+str(error.code)) from None
  except urllib.error.URLError:raise RuntimeError('Transcription network error; pending retained.') from None
  audio.json_write(target,{'audio_sha256':sha(dry),'response':result});pending.unlink()
  print('ASR',a['id'],c['id'],json.dumps(result.get('text',''),ensure_ascii=True),flush=True)
 with ThreadPoolExecutor(max_workers=2) as pool:
  for _ in pool.map(one,jobs):pass

# A scream can be transcribed as an interjection. Actual vocabulary is flagged.
def lexical_words(result):
 allowed={'ah','aah','agh','ugh','uh','huh','hmm','mm','mhm','hm','oh','ooh','ow','eh','ha','hah','h','a','kh','gh','grr'}
 flags=[]
 for w in result.get('words',[]):
  if w.get('type')=='audio_event' and re.search(r'laugh|giggl|chuckl|singing|speaking|hiccup',w.get('text',''),re.I):flags.append({'text':w['text'],'start':w.get('start'),'end':w.get('end'),'reason':'unexpected vocal reaction'})
  if w.get('type')!='word':continue
  for token in re.findall(r"[\w']+",w.get('text','').lower()):
   if token in allowed or re.fullmatch(r'(a+h*|a+g+h*|u+h*|u+g+h*|u+r+g+h*|n+g+h*|g+h+r*|k+h*|h+m*|m+h*|o+h*|h+a*h*)',token):continue
   flags.append({'text':token,'start':w.get('start'),'end':w.get('end')})
 return flags

def vocal_units(result):
 return sum(1 for w in result.get('words',[]) if w.get('type') in ('word','audio_event') and not re.search(r'inhale|exhale|pant|sigh|breath',w.get('text',''),re.I))

def compact_source(source,destination):
 # Retain the cry attack and tail, remove dead air, and preserve pitch when
 # a generated sustained cry needs time compression. Export has a hard cap.
 with wave.open(str(source)) as w:
  assert (w.getnchannels(),w.getframerate(),w.getsampwidth())==(1,22050,2)
  rate=w.getframerate();pcm=array.array('h',w.readframes(w.getnframes()))
 peak=max(abs(x) for x in pcm);threshold=max(200,peak*.035)
 first=next(i for i,x in enumerate(pcm) if abs(x)>=threshold)
 last=len(pcm)-1-next(i for i,x in enumerate(reversed(pcm)) if abs(x)>=threshold)
 start=max(0,first/rate-.006);end=min(len(pcm)/rate,(last+1)/rate+.045)
 active=end-start;factor=max(1,active/2.8);remaining=factor;tempo=[]
 while remaining>2:tempo.append('atempo=2');remaining/=2
 tempo.append(f'atempo={remaining:.8f}')
 duration=min(active/factor,3);fade=max(0,duration-.055)
 filters=f'atrim=start={start:.8f}:end={end:.8f},asetpts=PTS-STARTPTS,'+','.join(tempo)+f',atrim=duration=3,afade=t=in:d=0.003,afade=t=out:st={fade:.8f}:d=0.055'
 subprocess.run([audio.ffmpeg(),'-hide_banner','-loglevel','error','-y','-i',str(source),'-vn','-ac','1','-af',filters,'-ar','22050','-c:a','pcm_s16le',str(destination)],check=True)
 with wave.open(str(destination)) as w:assert w.getnframes()<=3*w.getframerate()
 return {'source_seconds':round(len(pcm)/rate,4),'active_seconds':round(active,4),'time_scale':round(factor,4)}

def write_header(manifest):
 actors=[a['id'] for a in manifest['actors']];causes=[c['id'] for c in manifest['causes']]
 effects=[e['id'] for e in read(ROOT/'data/effects.json')['effects']]
 lines=['// Generated by vector-fields/death_voice_workshop.py.', '#ifndef VF_DEATH_CATALOG_H', '#define VF_DEATH_CATALOG_H', '#include "vf_status_catalog.h"', 'namespace vfd {', 'enum Id {'+','.join('D_'+c for c in causes)+'};', 'struct Cause {const char* id;int effect;};', 'static const Cause Causes[]={']
 for c in causes:lines.append('{"'+c+'",'+('vfs::S_'+c if c in effects else '-1')+'},')
 lines+=['};','enum {CauseCount=sizeof(Causes)/sizeof(Causes[0]),ActorCount='+str(len(actors))+'};','struct Clip {int actor,cause;const char* path;float duration;};','static const Clip Clips[]={']
 by_id={(c['actor'],c['cause']):c for c in manifest['clips']}
 for ai,a in enumerate(actors):
  for ci,c in enumerate(causes):
   clip=by_id[a,c];lines.append('{%d,%d,"%s",%.4ff},'%(ai,ci,clip['path'],clip['duration']))
 lines+=['};','enum {ClipCount=sizeof(Clips)/sizeof(Clips[0])};','inline int Index(int actor,int cause){return actor>=0&&actor<ActorCount&&cause>=0&&cause<CauseCount?actor*CauseCount+cause:-1;}','}','#endif','']
 (ROOT.parent/'game_shared/vf_death_catalog.h').write_text('\n'.join(lines),encoding='utf-8')

def build():
 d=catalog();clips=[];missing=[];flags=[]
 for a,c in items():
  s=stem(a,c);meta=s.with_suffix('.json');dry=s.with_name(s.name+'_source_master.wav')
  if not meta.exists() or not dry.exists():missing.append(a['id']+'/'+c['id']);continue
  m=read(meta);assert m['text']==c['text'] and m['sha256']==sha(s.with_suffix('.mp3'))
  assert m['voice_id']==read((DATA.parent/a['voice_reference']).resolve())['response']['voice_id']
  check=s.with_name(s.name+'_asr.json')
  if not check.exists():missing.append(a['id']+'/'+c['id']+' speech verification');continue
  verification=read(check);assert verification['audio_sha256']==sha(dry)
  suspect=lexical_words(verification['response'])
  units=vocal_units(verification['response'])
  if not 1<=units<=d['max_vocalizations']:suspect.append({'reason':'vocal attack count','units':units})
  if suspect:flags.append({'actor':a['id'],'cause':c['id'],'words':suspect});continue
  master=s.with_name(s.name+'_master.wav');game=s.with_suffix('.wav')
  compact=s.with_name(s.name+'_dry_master.wav');edit=compact_source(dry,compact)
  filters=c['master_filter']+',atrim=duration=3,alimiter=limit=0.9:level=false'
  subprocess.run([audio.ffmpeg(),'-hide_banner','-loglevel','error','-y','-i',str(compact),'-vn','-ac','1','-af',filters,'-ar','22050','-c:a','pcm_s16le',str(master)],check=True)
  voices.game_wav(master,game)
  with wave.open(str(game)) as w:
   assert (w.getnchannels(),w.getframerate(),w.getsampwidth())==(1,11025,1)
   samples=w.readframes(w.getnframes());duration=w.getnframes()/w.getframerate()
  assert .15<duration<=3 and max(abs(x-128) for x in samples)>10
  assert not any(x in (0,255) for x in samples)
  clips.append({'actor':a['id'],'cause':c['id'],'path':'vf_deaths/'+a['id']+'/'+game.name,'text':'','subtitle':None,'duration':round(duration,4),'sha256':sha(game),'voice_id':m['voice_id'],'speech_check':'nonverbal/interjections only','master_filter':c['master_filter'],'edit':edit,'vocalizations':units})
 audio.json_write(ROOT/'build/death-voices-review.json',{'missing':missing,'lexical_flags':flags,'prepared_clips':len(clips)})
 if missing or flags:raise RuntimeError(f'Death bank not complete: {len(missing)} missing, {len(flags)} speech flags. See build/death-voices-review.json.')
 manifest={'schema':1,'asset_version':d['asset_version'],'max_duration_seconds':3,'max_vocalizations':d['max_vocalizations'],'integration':'native-death-hooks','nonverbal_only':True,'actors':d['actors'],'causes':d['causes'],'tactical_fallback':d['tactical_fallback'],'default_cause':'standard','format':d['format'],'clips':clips,'legacy_spoken_death_clips':'deprecated; never emitted by native death hooks','engine_note':'Separate VFDeath actor/cause catalog; native positional CHAN_VOICE audio; no captions.'}
 audio.json_write(ASSETS/'manifest.json',manifest)
 write_header(manifest)
 with zipfile.ZipFile(ASSETS/'death-bank-game.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
  archive.write(ASSETS/'manifest.json','vf/death-voice-manifest.json')
  for clip in clips:archive.write(ASSETS/clip['path'].removeprefix('vf_deaths/'),'sound/'+clip['path'])
 audio.json_write(ROOT/'build/death-voices-verification.json',{'asset_version':d['asset_version'],'actors':6,'causes':17,'clips':len(clips),'maximum_seconds':max(c['duration'] for c in clips),'minimum_seconds':min(c['duration'] for c in clips),'maximum_vocalizations':max(c['vocalizations'] for c in clips),'bytes':sum((ASSETS/c['path'].removeprefix('vf_deaths/')).stat().st_size for c in clips),'seconds':round(sum(c['duration'] for c in clips),2),'format':'mono PCM 11025 Hz / 8-bit','integration':'native-death-hooks','checks':['all six existing voice identities retained','standard, eight elements and eight reactions complete','five tactical states explicitly fall back to standard','scripts contain only vocalizations and performance tags','Scribe verification contains only audio events and nonverbal interjections','game WAV hashes, duration, nonsilence and no full-scale clipping validated','raw MP3/source masters retained; compact dry and processed 22050 Hz masters are at most three seconds','one or two vocalizations per script; no long agony or terminal breath sequences','one or two recognized vocal attacks per take; no unwanted speech, laughter or hiccups','empty caption text; separate generated death catalog for native hooks','game-only ZIP contains exactly 102 game WAVs and the manifest; no masters or rejected takes'],'limits':['ASR is an automated lexical check, not a guarantee of acting quality or cause recognition. Human listening remains useful.']})
 preview();print('BUILT',len(clips),'contextual death screams',flush=True)

def deploy(mod):
 manifest=read(ASSETS/'manifest.json')
 assert manifest['integration']=='native-death-hooks' and len(manifest['clips'])==102
 for clip in manifest['clips']:
  source=ASSETS/clip['path'].removeprefix('vf_deaths/')
  assert sha(source)==clip['sha256']
  target=mod/'sound'/clip['path'];target.parent.mkdir(parents=True,exist_ok=True)
  shutil.copy2(source,target)
 target=mod/'vf/death-voice-manifest.json';target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(ASSETS/'manifest.json',target)
 return manifest

def preview():
 d=catalog();cards=[]
 for a in d['actors']:
  content=[f'<article><h2>{html.escape(a["name"])}</h2>']
  for c in d['causes']:
   s=stem(a,c);game=s.with_suffix('.wav')
   if not game.exists():continue
   rel=game.relative_to(ASSETS).as_posix();master=s.with_name(s.name+'_master.wav').relative_to(ASSETS).as_posix();dry=s.with_name(s.name+'_dry_master.wav').relative_to(ASSETS).as_posix()
   content.append(f'<div class="clip" data-cause="{c["id"]}"><h3>{html.escape(c["name"])}</h3><p>{html.escape(c["performance"])}</p><audio controls preload="none" src="{rel}"></audio><details><summary>Comparer les masters</summary><p>Master avec traitement de la cause</p><audio controls preload="none" src="{master}"></audio><p>Cri brut raccourci</p><audio controls preload="none" src="{dry}"></audio></details></div>')
  cards.append(''.join(content)+'</article>')
 options=''.join(f'<option value="{c["id"]}">{html.escape(c["name"])}</option>' for c in d['causes'])
 doc='<html lang="fr"><meta charset="utf-8"><title>Cris de mort / Vector Fields</title><style>body{font:16px system-ui;background:#111922;color:#eef3f8;margin:30px}h1{font-size:28px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}article{padding:16px;background:#202c38;border-radius:8px}.clip{border-top:1px solid #58697b;padding:12px 0}h3{font-size:16px}p{line-height:1.5;color:#bdcbd7}audio{width:100%}select{padding:10px;margin:14px 0}</style><h1>Six personnages / 17 types de mort</h1><p>Cris brefs sans dialogues, trois secondes maximum. Format Half-Life : mono, 11025 Hz, 8 bits. Banque integree aux morts du joueur, des bots et des cibles du stand. Les etats tactiques utilisent la mort standard.</p><label>Comparer : <select id="cause">'+options+'</select></label><main>'+''.join(cards)+'</main><script>function update(){document.querySelectorAll(".clip").forEach(c=>c.hidden=c.dataset.cause!==document.querySelector("#cause").value)}document.querySelector("#cause").onchange=update;update();document.addEventListener("play",e=>document.querySelectorAll("audio").forEach(a=>{if(a!==e.target)a.pause()}),true)</script></html>'
 (ASSETS/'listen.html').write_text(doc,encoding='utf-8')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['generate','check-speech','build','preview']);p.add_argument('--limit',type=int,default=102);p.add_argument('--ensure',action='store_true');args=p.parse_args()
 if args.command=='generate':generate(args.limit)
 elif args.command=='check-speech':speech_check(args.limit)
 elif args.command=='build':
  if args.ensure and (ASSETS/'manifest.json').exists():
   manifest=read(ASSETS/'manifest.json');source=catalog()
   assert manifest['integration']=='native-death-hooks' and manifest['asset_version']==source['asset_version']
   assert len(manifest['clips'])==102
   for clip in manifest['clips']:assert sha(ASSETS/clip['path'].removeprefix('vf_deaths/'))==clip['sha256']
   write_header(manifest);print('READY 102 contextual death screams',flush=True)
  else:build()
 else:preview()

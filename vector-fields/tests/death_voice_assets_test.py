"""Verify the integrated nonverbal death bank and offline exports."""
import hashlib,json,re,wave,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'assets/audio/operator-deaths'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def run():
 manifest=read(ASSETS/'manifest.json');source=read(ROOT/'data/death_voices.json');effects=read(ROOT/'data/effects.json')['effects']
 expected={'standard'}|{e['id'] for e in effects if e['kind']<2}
 tactical={e['id'] for e in effects if e['kind']==2}
 assert len(expected)==17 and len(manifest['clips'])==102
 assert manifest['integration']=='native-death-hooks' and manifest['nonverbal_only']
 assert manifest['asset_version']==source['asset_version']==2
 assert manifest['max_duration_seconds']==source['max_duration_seconds']==3
 assert manifest['max_vocalizations']<=2
 for cause in source['causes']:
  script=re.sub(r'\[[^\]]+\]','',cause['text'])
  assert 1<=len(re.findall(r'[A-Za-z][A-Za-z-]*',script))<=2
  assert '[exhales]' not in cause['text'] and '[sighs]' not in cause['text']
 assert set(manifest['tactical_fallback'])==tactical and set(manifest['tactical_fallback'].values())=={'standard'}
 voice_ids=set();seen=set()
 for actor in manifest['actors']:
  voice_ids.add(read(ROOT/'assets/audio/operators'/actor['id']/'voice.json')['response']['voice_id'])
  assert {c['cause'] for c in manifest['clips'] if c['actor']==actor['id']}==expected
 assert len(voice_ids)==6
 for clip in manifest['clips']:
  assert clip['cause'] not in tactical and (clip['actor'],clip['cause']) not in seen;seen.add((clip['actor'],clip['cause']))
  p=ASSETS/clip['path'].removeprefix('vf_deaths/');assert hashlib.sha256(p.read_bytes()).hexdigest()==clip['sha256']
  assert clip['text']=='' and clip['subtitle'] is None
  assert 1<=clip['vocalizations']<=2
  assert clip['voice_id']==read(ROOT/'assets/audio/operators'/clip['actor']/'voice.json')['response']['voice_id']
  with wave.open(str(p)) as w:
   assert (w.getnchannels(),w.getframerate(),w.getsampwidth())==(1,11025,1)
   duration=w.getnframes()/w.getframerate();samples=w.readframes(w.getnframes())
  assert abs(duration-clip['duration'])<.001 and .15<duration<=3
  assert max(abs(s-128) for s in samples)>10 and not any(s in (0,255) for s in samples)
  for suffix in ['_master.wav','_dry_master.wav']:
   with wave.open(str(p.with_name(p.stem+suffix))) as w:
    assert (w.getnchannels(),w.getframerate(),w.getsampwidth())==(1,22050,2)
    assert w.getnframes()<=3*w.getframerate()
  assert p.with_suffix('.mp3').exists() and p.with_name(p.stem+'_asr.json').exists()
  assert p.with_name(p.stem+'_source_master.wav').exists()
 assert len(list(ASSETS.glob('*/*_v'+str(source['asset_version'])+'.wav')))==102 and not list(ASSETS.rglob('*.pending'))
 with zipfile.ZipFile(ASSETS/'death-bank-game.zip') as archive:
  assert set(archive.namelist())=={'vf/death-voice-manifest.json'}|{'sound/'+c['path'] for c in manifest['clips']}
  for clip in manifest['clips']:assert hashlib.sha256(archive.read('sound/'+clip['path'])).hexdigest()==clip['sha256']
 page=(ASSETS/'listen.html').read_text(encoding='utf-8')
 for src in re.findall(r'src="([^"]+)"',page):assert (ASSETS/src).is_file(),src
 print('PASS death bank: 102 nonverbal clips <=3 seconds; 6 original voices; 17 causes; tactical fallback; PCM, hashes, clean masters, silent captions and listening page.')
if __name__=='__main__':run()

"""Validate reusable audio, voice filtering and actual native five-mode HUD transitions."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import struct
import sys
import wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from headgear_preview import stage, asset_library
from headgear_audio import runtime_files, dialogue_entries
from native_workspace import port
from build_headgear_hud import runtime_files as hud_runtime_files
OUT = ROOT / 'docs/validation/headgear/feedback'

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def samples(path):
    with wave.open(str(path)) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 1, 11025), path
        return (np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.uint8).astype(float)-128)/128

def assets():
    hud = read(ROOT/'generated/headgear-hud/manifest.json')
    assert [entry['type'] for entry in hud['assets']]==[1,2,3,4,5]
    for source,_ in hud_runtime_files():assert source.is_file()
    clear=[]
    for entry in hud['assets']:
        painting=ROOT/'assets/headgear/hud/sources'/entry['source']
        assert digest(painting)==entry['source_sha256']
        frame=Image.open(ROOT/'assets/headgear/hud/frames'/(entry['id']+'.png'))
        assert frame.mode=='RGBA' and frame.size==(1024,576)
        data=(ROOT/'generated/headgear-hud'/(entry['id']+'.spr')).read_bytes()
        header=struct.unpack('<4siifiiifi',data[:36])
        assert header[:3]==(b'IDSP',32,2) and header[4:7]==(1024,576,1)
        assert data[56:]==frame.tobytes(),'Packed sprite must retain every authored RGBA pixel'
        alpha=np.asarray(frame)[:,:,3]
        assert alpha[260:316,461:563].max()<=8
        assert (alpha>200).mean()>.10 and (alpha<8).mean()>.20
        clear.append(float((alpha<8).mean()))
    manifest = read(ROOT / 'generated/headgear-audio/manifest.json')
    actors = read(ROOT / 'data/voices.json')['actors']
    expected={clip['path'] for clip,event in dialogue_entries()}
    assert len(manifest['clips']) == 24 and len(manifest['sounds']) == 6
    assert {entry['original'] for entry in manifest['muffled']}==expected
    assert all(entry['original'].startswith('vf_voices/') for entry in manifest['muffled'])
    assert not any(entry['path'] in expected for entry in manifest['clips'])
    assert not any((ROOT/'generated/headgear-audio/sound/vf_muffle').rglob('d_*.wav'))
    assert not any((ROOT/'generated/headgear-audio/sound/vf_muffle').rglob('h_*.wav'))
    for source, _ in runtime_files():assert source.is_file()
    for actor, data in enumerate(actors):
        rows = [c for c in manifest['clips'] if c['actor'] == actor]
        assert sorted(c['category'] for c in rows) == [0, 1, 2, 3]
        voice = read(ROOT / 'assets/audio/operators' / data['id'] / 'voice.json')['response']['voice_id']
        assert all(c['voice_id'] == voice for c in rows)
    comparisons = []
    for row in manifest['muffled']:
        filtered = ROOT / 'generated/headgear-audio/sound' / row['path']
        original = row['original']
        if original.startswith('vf_voices/'):
            source = ROOT / 'assets/audio/operators' / original.removeprefix('vf_voices/')
        elif original.startswith('vf_deaths/'):
            source = ROOT / 'assets/audio/operator-deaths' / original.removeprefix('vf_deaths/')
        else:source = ROOT / 'generated/headgear-audio/sound' / original
        dry, wet = samples(source), samples(filtered)
        assert abs(len(dry)-len(wet)) <= 3, (original, len(dry), len(wet))
        assert np.max(np.abs(wet)) > .06 and np.max(np.abs(wet)) < .95
        assert not np.array_equal(dry, wet)
        def high_fraction(values):
            spectrum = np.abs(np.fft.rfft(values*np.hanning(len(values))))**2
            frequencies = np.fft.rfftfreq(len(values), 1/11025)
            return float(spectrum[frequencies>3000].sum()/max(spectrum.sum(), 1e-10))
        a, b = high_fraction(dry), high_fraction(wet)
        if a > .015:comparisons.append(b/a)
    assert len(comparisons)>100 and float(np.median(comparisons))<.4
    for row in manifest['sounds']:
        with wave.open(str(ROOT / 'generated/headgear-audio/sound' / row['path'])) as wav:
            assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 22050)
            assert .2 < wav.getnframes()/22050 < 1.6
    result = dict(passed=True, actor_identities_preserved=6, new_lines=24, reusable_sfx=6,
                  authored_hud_textures=5, texture_clear_fractions=clear,
                  filtered_existing_recordings=len(expected), no_voice_resynthesis_for_filter=True,
                  dialogue_events=manifest['muffle_policy']['dialogue_events'],
                  activation_voice_normal=True,death_recordings_not_duplicated=True,
                  median_high_frequency_fraction_ratio=float(np.median(comparisons)),
                  original_voice_catalog_sha256=digest(ROOT.parent/'game_shared/vf_voice_catalog.h'))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'assets.json').write_text(json.dumps(result, indent=2))
    print('PASS headgear feedback assets:', result, flush=True)

def native(candidate=None):
    engine, mod = stage('headgear-feedback-native',candidate)
    captures = []
    lines = ['wait 180','developer 2','con_notifytime -1','gl_vsync 0','fps_max 60','host_framerate .016666667',
             'sv_cheats 1','vf_voice_subtitles 0','weapon_9mmAR','wait 45','firstperson']
    helmets = read(ROOT/'data/headgear.json')
    actors = [a['id'] for a in read(ROOT/'data/voices.json')['actors']]
    def snap(name):
        captures.append(name)
        lines.extend(['vf_headgear_hud_info',f'screenshot scrshots/{name}.png','wait 1'])
    for i, gear in enumerate(helmets):
        key=gear['id']
        lines.extend(['vf_operator','wait 25',f'vf_item {key}','vf_commit','wait 25','vf_operator','wait 10',
                      f'cmd vf_voice_set {actors[i]}','wait 10','cmd vf_voice_preview reload','wait 5'])
        snap(key+'_initial')
        lines.extend(['vf_headgear_toggle','wait 90'])
        snap(key+'_raised')
        lines.extend(['cmd vf_voice_preview reload','wait 180','vf_headgear_toggle','wait 25'])
        snap(key+'_transition')
        lines.extend(['wait 65'])
        snap(key+'_lowered')
        lines.extend(['thirdperson','wait 15'])
        snap(key+'_third')
        lines.extend(['firstperson','wait 15'])
    # Audition all categories with each existing actor through the separate bank.
    lines.extend(['vf_operator','wait 25','vf_item helmet_gas_mask','vf_commit','wait 25','vf_operator','wait 10'])
    for actor in actors:
        lines.extend([f'cmd vf_voice_set {actor}','wait 2'])
        for category in ('generic','visor','mask','goggles'):
            lines.extend([f'cmd vf_headgear_voice_preview {category}','wait 8'])
    # Owner-only complaints must use the same sealed sample, even with captions off.
    lines.extend(['cmd vf_voice_preview respawn','wait 10'])
    # Exercise the same native dispatcher for every current dialogue family.
    events=[e for e in read(ROOT/'data/voices.json')['events'] if e!='death']
    lines.extend(['cmd vf_voice_set rocco','wait 5','echo FILTER_CLOSED_BEGIN'])
    for event in events:lines.extend([f'cmd vf_voice_preview {event}','wait 6'])
    lines.extend(['cmd vf_voice_preview death','wait 8','echo FILTER_CLOSED_END','vf_headgear_toggle','wait 90','echo FILTER_OPEN_BEGIN'])
    for event in events:lines.extend([f'cmd vf_voice_preview {event}','wait 6'])
    lines.extend(['cmd vf_voice_preview death','wait 8','echo FILTER_OPEN_END','vf_engine_stats','quit'])
    for part, start in enumerate(range(0,len(lines),100)):
        chunk=lines[start:start+100]
        if start+100<len(lines):chunk.append(f'exec feedback_{part+1:03}.cfg')
        (mod/f'feedback_{part:03}.cfg').write_text('\n'.join(chunk)+'\n',encoding='ascii')
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir',str(asset_library()),'-game',mod.name,
        '-dev','2','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','feedback.log',
        '-port',str(port()),'-clientport',str(port()),'+exec','lab_controls.cfg','+sv_cheats','1','+developer','2','+map','vf_range','+exec','feedback_000.cfg'],
        cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    try:process.wait(timeout=180)
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=8)
    assert process.returncode==0
    log=(engine/'feedback.log').read_text(errors='replace')
    assert 'v4 connected' in log and f'lines=24 sounds=6 muffled={len(list(dialogue_entries()))}' in log
    assert not any(t in log for t in ('Host_Error','SV_Error','Could not load','VFState rejected','S_LoadSound:','dims out of range','Error: Image:'))
    assert len(re.findall(r'VFHeadgear sfx: player=1',log))==11
    loaded=re.findall(r'VFHeadgear texture: type=(\d) asset=(\w+) loaded=1',log)
    assert set(int(t) for t,_ in loaded)=={1,2,3,4,5},loaded
    hud=re.findall(r'VFHeadgear HUD: type=(\d) cover=([\d.]+) active=(\d) thirdperson=(\d)',log)
    assert len(hud)==25,len(hud)
    for i, gear in enumerate(helmets):
        group=hud[i*5:(i+1)*5]
        assert int(group[0][0])==gear['type'] and float(group[0][1])==1
        assert float(group[1][1])==0 and int(group[1][2])==0
        assert .001<float(group[2][1])<.999
        assert float(group[3][1])==1 and int(group[3][2])==1
        assert group[4]==('0','0.0000','0','1')
    voices=re.findall(r'VFHeadgear voice: player=1 actor=(\w+) category=(\d) sample=(\S+)',log)
    assert len(voices)==29,(len(voices),voices)
    assert all(sample.startswith('vf_headgear/voices/') for _,_,sample in voices)
    announces=re.findall(r'VFHeadgear voice: .*?audition=0 cover=([\d.]+)',log)
    assert len(announces)==5 and all(float(cover)<.01 for cover in announces)
    for actor in actors:
        assert set(int(c) for a,c,_ in voices if a==actor)=={0,1,2,3}
    assert len(re.findall(r'VFHeadgear voice received:',log))==29
    initial=log.split('FILTER_CLOSED_BEGIN')[0]
    reloads=re.findall(r'VFVoice play: player=1 actor=\w+ event=reload clip=\d+ sample=(\S+)',initial)
    assert len(reloads)==10
    for i,gear in enumerate(helmets):
        assert reloads[i*2].startswith('vf_muffle/')==(gear['type'] in (1,2,5))
        assert reloads[i*2+1].startswith('vf_voices/')
    assert 'VFVoice private played: player=1' in log
    assert re.search(r'VFVoice private played: player=1 clip=\d+ sample=vf_muffle/',log)
    for state,prefix in (('CLOSED','vf_muffle/'),('OPEN','vf_voices/')):
        block=log.split('FILTER_'+state+'_BEGIN')[1].split('FILTER_'+state+'_END')[0]
        played=re.findall(r'VFVoice play: player=1 actor=rocco event=(\w+) clip=\d+ sample=(\S+)',block)
        assert {event for event,_ in played}==set(events),state
        assert all(sample.startswith(prefix) for _,sample in played),(state,played)
        deaths=re.findall(r'VFDeath play: .*?sample=(\S+)',block)
        assert len(deaths)==1 and deaths[0].startswith('vf_deaths/'),(state,deaths)
    poses=re.findall(r'right_error=([\d.]+) weapon_error=([\d.]+)',log)
    assert poses and all(float(a)==float(b)==0 for a,b in poses)
    OUT.mkdir(parents=True,exist_ok=True)
    shutil.copy2(engine/'feedback.log',OUT/'native.log')
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
    board=Image.new('RGB',(1600,len(helmets)*486),'#141e27');draw=ImageDraw.Draw(board)
    texture_pixel_errors=[]
    for row,gear in enumerate(helmets):
        asset=next(e for e in read(ROOT/'generated/headgear-hud/manifest.json')['assets'] if e['type']==gear['type'])
        texture=np.asarray(Image.open(ROOT/'assets/headgear/hud/frames'/(asset['id']+'.png')).resize((1280,720),Image.Resampling.BILINEAR)).astype(float)
        opaque=texture[:,:,3]>254
        actual=np.asarray(Image.open(mod/'scrshots'/f'{gear["id"]}_lowered.png').convert('RGB')).astype(float)
        error=np.abs(actual-texture[:,:,:3]).mean(axis=2)
        assert np.median(error[opaque])<50,(gear['id'],'Loaded texture must actually appear in captured pixels',np.median(error[opaque]))
        texture_pixel_errors.append(dict(type=gear['type'],median_rgb_error=float(np.median(error[opaque]))))
        for col,(state,label) in enumerate((('lowered','Baissé / actif'),('raised','Relevé / vue libre'))):
            source=mod/'scrshots'/f'{gear["id"]}_{state}.png'
            assert Image.open(source).size==(1280,720)
            x=col*800;y=row*486
            draw.text((x+10,y+5),gear['name']+' — '+label,font=font,fill='#e5f3ed')
            board.paste(Image.open(source).resize((800,450)),(x,y+36))
            shutil.copy2(source,OUT/source.name)
    image=ROOT/'docs/images/headgear-feedback-in-game.jpg';board.save(image,quality=94)
    report=dict(passed=True, hud_types=5, transitions=5, positional_sfx=11, headgear_voice_packets=29,
                authored_rgba_textures_loaded=5,
                captured_texture_pixels_verified=True,texture_pixel_errors=texture_pixel_errors,
                normal_activation_before_face_covered=True,all_dialogue_events_filtered_and_restored=events,
                closed_and_raised_death_cries_original=True,
                all_six_actors_and_four_categories=True, closed_voice_filtered=True, raised_voice_restored=True,
                goggles_leave_voice_clear=True, third_person_clear=True, private_respawn_filtered=True,
                right_hand_and_weapon_error=0, image=str(image),
                client_sha256=digest(mod/'cl_dlls/client.dll'), server_sha256=digest(mod/'dlls/hl.dll'), renderer_sha256=digest(engine/'ref_gl.dll'))
    (OUT/'native.json').write_text(json.dumps(report,indent=2))
    print('PASS native headgear feedback:',report,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true');parser.add_argument('--candidate-dir',type=Path);args=parser.parse_args()
    native(args.candidate_dir) if args.native else assets()

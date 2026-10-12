"""Encode review frames; the disposable workspace is retired after encoding."""
import argparse,json,sys
from pathlib import Path
import bpy

OUT=Path(__file__).resolve().parents[1]/'docs/validation/traversal/transitions'
parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[])
if args.manifest:OUT=args.manifest.parent
report=json.loads((OUT/'capture.json').read_text())
paths=sorted(Path(report['frames_directory']).glob('frame_*.png'))
assert len(paths)==report['frames']
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=len(paths)
scene.render.threads_mode='FIXED';scene.render.threads=1
scene.render.resolution_x=report['width'];scene.render.resolution_y=report['height']
scene.render.resolution_percentage=100;scene.render.fps=report['fps']
scene.view_settings.view_transform='Standard';scene.render.use_sequencer=True
scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
scene.render.ffmpeg.constant_rate_factor='HIGH';scene.render.ffmpeg.ffmpeg_preset='GOOD'
scene.render.ffmpeg.audio_codec='NONE'
strips=scene.sequence_editor_create().strips
image=strips.new_image('Moteur GoldSrc',str(paths[0]),channel=1,frame_start=1)
for p in paths[1:]:image.elements.append(p.name)
image.frame_final_duration=len(paths);image.colorspace_settings.name='sRGB'
font=bpy.data.fonts.load('C:/Windows/Fonts/arial.ttf')
bar=strips.new_effect('Bandeau',type='COLOR',channel=2,frame_start=1,frame_end=len(paths)+1)
bar.color=(.012,.018,.027);bar.transform.scale_y=48/report['height']
bar.transform.offset_y=(report['height']-48)/2;bar.blend_type='ALPHA_OVER'
for i,event in enumerate(report['timeline']):
    end=report['timeline'][i+1]['frame']+1 if i+1<len(report['timeline'])else len(paths)+1
    title={'climb':'Remontée depuis la suspension','slide':'Glissade : entrée, maintien, sortie',
           'drop':'Ctrl : lâcher puis retour au combat','vault':'Muret : appui gauche et passage de l’autre côté',
           'stepup':'Plateforme : appui et montée sur le dessus','body':'Corps visible en regardant vers le bas',
           'crouch':'Accroupi : visée, tir et rechargement','hang':'Suspension : vue du corps contre le mur'}[event['gesture']]
    if event.get('action'):title={'shoot':'Glissade : visée et tir','reload':'Glissade : rechargement'}[event['action']]
    view='Première personne'if event['view']=='first-person'else'Troisième personne'
    strip=strips.new_effect(f'Vue {i}',type='TEXT',channel=3,frame_start=event['frame']+1,frame_end=end)
    strip.text=view+' — '+title;strip.font=font;strip.font_size=21
    strip.color=(.93,.96,1,1);strip.location=(.02,.955)
    strip.alignment_x='LEFT';strip.anchor_x='LEFT';strip.anchor_y='CENTER';strip.blend_type='ALPHA_OVER'
movie=OUT/('appuis-corps-franchissements.mp4'if report.get('posture')else'glissade-tir-rechargement.mp4'if report.get('combat')else'glissade-courte.mp4'if report.get('slide_only')else'montee-glissade-lacher.mp4');scene.render.filepath=str(movie)
bpy.ops.render.render(animation=True)
clip=bpy.data.movieclips.load(str(movie))
assert tuple(clip.size)==(report['width'],report['height'])and clip.frame_duration==len(paths)
report['video']=str(movie);report['duration_seconds']=len(paths)/report['fps']
if report.get('combat'):
    report['videos']={}
    for view,name in [('first-person','glissade-combat-premiere-personne.mp4'),('third-person','glissade-combat-troisieme-personne.mp4')]:
        events=[(i,event)for i,event in enumerate(report['timeline'])if event['view']==view]
        scene.frame_start=events[0][1]['frame']+1
        last=events[-1][0]+1
        scene.frame_end=report['timeline'][last]['frame']if last<len(report['timeline'])else len(paths)
        path=OUT/name;scene.render.filepath=str(path);bpy.ops.render.render(animation=True)
        clip=bpy.data.movieclips.load(str(path))
        assert clip.frame_duration==scene.frame_end-scene.frame_start+1
        report['videos'][view]=str(path)
(OUT/'capture.json').write_text(json.dumps(report,indent=2))
print('PASS encoded transitions',str(movie),movie.stat().st_size)

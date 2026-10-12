"""Encode the native PNG recording using Blender's bundled H.264 encoder."""
import argparse,json,sys
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/validation/traversal/video'
parser=argparse.ArgumentParser();parser.add_argument('--revision',default='')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
assert all(c.isalnum() or c=='-' for c in args.revision),'invalid video revision'
if args.revision:OUT=OUT.with_name('video-'+args.revision)
report=json.loads((OUT/'capture.json').read_text(encoding='utf-8'))
paths=sorted(Path(report['frames_directory']).glob('frame_*.png'))
assert len(paths)==report['frames']
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=len(paths)
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.fps=report['fps'];scene.view_settings.view_transform='Standard'
scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
scene.render.ffmpeg.constant_rate_factor='HIGH';scene.render.ffmpeg.ffmpeg_preset='GOOD'
scene.render.ffmpeg.audio_codec='NONE';scene.render.use_sequencer=True
editor=scene.sequence_editor_create();strips=editor.strips
image=strips.new_image('Capture du moteur',str(paths[0]),channel=1,frame_start=1)
for path in paths[1:]:image.elements.append(path.name)
image.frame_final_duration=len(paths)
image.colorspace_settings.name='sRGB'
font=bpy.data.fonts.load('C:/Windows/Fonts/arial.ttf')

def bar(name,y,height,channel):
    strip=strips.new_effect(name,type='COLOR',channel=channel,frame_start=1,frame_end=len(paths)+1)
    strip.color=(.012,.018,.027);strip.transform.scale_y=height/720;strip.transform.offset_y=y-360
    strip.blend_type='ALPHA_OVER';return strip

def text(name,label,begin,end,channel,y,size=25):
    strip=strips.new_effect(name,type='TEXT',channel=channel,frame_start=begin,frame_end=end)
    strip.text=label;strip.font=font;strip.font_size=size;strip.color=(.93,.96,1,1)
    strip.location=(.025,y/720);strip.alignment_x='LEFT';strip.anchor_x='LEFT';strip.anchor_y='CENTER'
    strip.blend_type='ALPHA_OVER';strip.use_shadow=True;return strip

# Narrow captions cover UI text, while leaving all of the character visible.
bar('Titre',690,60,2)
title=('Visée à gauche : bras d’appui tendu, torse en arrière'if args.revision=='appui-gauche'else 'Suspension : garde face au mur, visée à hauteur d’épaule')
text('Vue',title,1,len(paths)+1,4,690,24)
bar('Direction',25,50,3)
for i,event in enumerate(report['timeline']):
    end=report['timeline'][i+1]['frame']+1 if i+1<len(report['timeline'])else len(paths)+1
    yaw=event['yaw'];signed=(yaw+180)%360-180
    label=('Suspension à deux mains'if event['label'].startswith('Suspension')else
           'Sortie de l’arme'if event['label'].startswith('Sortie')else
           'Retour à deux mains'if event['label'].startswith('Retour')else
           f'Garde : {signed:+.0f}° — canon vers le haut / tir bloqué'if not event.get('fire_allowed',True)else
           f'Tir : {signed:+.0f}° — '+('appui gauche tendu'if args.revision=='appui-gauche'and 75<=signed<=135 else 'caméra fixe / lecture accélérée'))
    text('Direction '+str(i),label,event['frame']+1,end,5,25,24)
movie=OUT/'suspension-tirs-troisieme-personne.mp4'
scene.render.filepath=str(movie)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Montage-suspension.blend'))
bpy.ops.render.render(animation=True)
assert movie.exists() and movie.stat().st_size>100000,movie
clip=bpy.data.movieclips.load(str(movie))
assert tuple(clip.size)==(1280,720) and clip.frame_duration==len(paths),(tuple(clip.size),clip.frame_duration)
report['video']=str(movie);report['duration_seconds']=len(paths)/report['fps']
report['encoding']='H.264 / MP4 / yuv420p, Blender bundled FFmpeg'
(OUT/'video.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS ENCODED VIDEO',str(movie),movie.stat().st_size,flush=True)

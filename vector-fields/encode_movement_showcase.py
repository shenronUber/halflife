"""Blender VSE: label and encode the six native clips as verified H.264 videos."""
import json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'docs/videos/mouvements-2026-10-12'
if '--'in sys.argv:
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if args.output:OUT=args.output.resolve()
report=json.loads((OUT/'capture.json').read_text());captures=Path(report['frames_directory'])
LABELS={'melee':('MÊLÉE','Poing gauche fermé · Frappe avec l’avant du canon · Reprise de l’arme'),
        'wallrun':('WALL RUN','Accroche volontaire · Cap conservé avec avancer · Regard ±90° · Au-delà : lâcher'),
        'backjump':('BACK JUMP','Depuis la suspension · Reculer + saut · Prise du mur opposé'),
        'reload':('RECHARGEMENT ACCROUPI','Début de l’animation · Dos stable · Reprise de la visée'),
        'parcours':('PARCOURS · ÉTUDE DE VOLUMES','Mêlée · Glissade · Wall run · Accroche · Rebond · Reprise · Montée'),
        'rebond_detail':('REBOND · RALENTI × 0,5','Lâcher · Impulsion · Rotation vers le regard · Bras vers la nouvelle prise')}
VIEWS={'first':'PREMIÈRE PERSONNE','third':'TROISIÈME PERSONNE'}

def scene_new():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
    scene.render.fps=60;scene.render.threads_mode='FIXED';scene.render.threads=1
    scene.render.use_sequencer=True;scene.view_settings.view_transform='Standard'
    return scene,scene.sequence_editor_create().strips

def encode(name,clips):
    scene,strips=scene_new();frame=1;timeline=[]
    bold=bpy.data.fonts.load('C:/Windows/Fonts/seguisb.ttf');regular=bpy.data.fonts.load('C:/Windows/Fonts/segoeui.ttf')
    for clip in clips:
        count=clip['frames'];key=clip['key'];timeline.append(dict(key=key,start=frame,end=frame+count-1))
        paths=[captures/f'{key}_{i:04}.png'for i in range(count)]
        assert all(p.exists()for p in paths)
        image=strips.new_image(key,str(paths[0]),channel=1,frame_start=frame)
        for p in paths[1:]:image.elements.append(p.name)
        image.frame_final_duration=count;image.colorspace_settings.name='sRGB'
        title,detail=LABELS[clip['feature']]
        for channel,text,font,size,y in [(3,title+'  ·  '+VIEWS[clip['view']],bold,25,.967),(4,detail,regular,18,.925)]:
            textstrip=strips.new_effect(key+str(channel),type='TEXT',channel=channel,frame_start=frame,frame_end=frame+count)
            textstrip.text=text;textstrip.font=font;textstrip.font_size=size;textstrip.color=(.94,.97,1,1)
            textstrip.location=(.022,y);textstrip.alignment_x='LEFT';textstrip.anchor_x='LEFT';textstrip.anchor_y='CENTER'
            textstrip.blend_type='ALPHA_OVER'
        frame+=count
    band=strips.new_effect('Bandeau',type='COLOR',channel=2,frame_start=1,frame_end=frame)
    band.color=(.012,.018,.027);band.transform.scale_y=72/720;band.transform.offset_y=(720-72)/2;band.blend_type='ALPHA_OVER'
    scene.frame_start=1;scene.frame_end=frame-1
    scene.render.image_settings.file_format='FFMPEG';scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
    scene.render.ffmpeg.constant_rate_factor='HIGH';scene.render.ffmpeg.ffmpeg_preset='GOOD';scene.render.ffmpeg.audio_codec='NONE'
    path=OUT/name;scene.render.filepath=str(path);bpy.ops.render.render(animation=True)
    assert path.exists()and path.stat().st_size>10000
    decoded=bpy.data.movieclips.load(str(path));assert tuple(decoded.size)==(1280,720)and decoded.frame_duration==frame-1
    print('PASS H.264',name,frame-1,'frames',flush=True)
    return dict(path=str(path),frames=frame-1,duration_seconds=(frame-1)/60,width=1280,height=720,fps=60,timeline=timeline)

videos={}
course=any(c['feature']=='parcours'for c in report['clips'])
melee_only=all(c['feature']=='melee'for c in report['clips'])
prefix='parcours'if course else'melee-poing'if melee_only else'features-verifiees'if any(c['feature']=='reload'for c in report['clips'])else'melee-wall-run-back-jump'
for kind,name in [('all',prefix+'.mp4'),('first',prefix+'-premiere-personne.mp4'),('third',prefix+'-troisieme-personne.mp4')]:
    clips=[c for c in report['clips']if kind=='all'or c['view']==kind]
    videos[kind]=encode(name,clips)

# Decode the delivered movie, not the PNG inputs, to check labels and framing.
scene,strips=scene_new();movie=strips.new_movie('MP4 livré',videos['all']['path'],channel=1,frame_start=1)
scene.render.image_settings.file_format='PNG'
previews=[]
for key in ['parcours_first','parcours_third','rebond_detail']if course else['melee_first','melee_third']if melee_only else['melee_first','wallrun_third','backjump_third']:
    event=next(e for e in videos['all']['timeline']if e['key']==key)
    sample=event['start']+({'parcours_first':120,'parcours_third':390,'rebond_detail':65}[key]if course else 48 if key.startswith('melee')else 75 if key=='wallrun_third'else 42)
    scene.frame_set(sample);path=OUT/(key+'-decoded.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    assert path.exists();previews.append(str(path))
report['videos']=videos;report['decoded_previews']=previews
(OUT/'video.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS three verified 720p/60 videos and three decoded review frames',flush=True)

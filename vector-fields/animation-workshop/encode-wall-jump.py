"""Encode captured game frames with Blender's bundled H.264 encoder."""
import json
from pathlib import Path
import bpy
OUT=Path(__file__).resolve().parents[1]/'docs/validation/traversal/wall-jump'
counts=json.loads((OUT/'video.json').read_text())
for key,count in counts.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=count+60
    scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
    scene.render.fps=60;scene.view_settings.view_transform='Standard'
    scene.render.image_settings.file_format='FFMPEG';scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
    scene.render.ffmpeg.constant_rate_factor='HIGH';scene.render.ffmpeg.ffmpeg_preset='GOOD'
    scene.render.ffmpeg.audio_codec='NONE';scene.render.use_sequencer=True
    strips=scene.sequence_editor_create().strips
    paths=[OUT/'captures'/(key+'_motion_'+str(i).zfill(3)+'.png')for i in range(count)]
    image=strips.new_image('Saut du mur',str(paths[0]),channel=1,frame_start=1)
    for path in [paths[0]]*30+paths[1:]+[paths[-1]]*30:image.elements.append(path.name)
    image.frame_final_duration=count+60;image.colorspace_settings.name='sRGB'
    scene.render.filepath=str(OUT/(key+'.mp4'));bpy.ops.render.render(animation=True)
    movie=OUT/(key+'.mp4');assert movie.exists()and movie.stat().st_size>10000
    print('PASS video',key,count,'game frames',flush=True)

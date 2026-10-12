"""Show the packed grip reference after Blender creates its editor spaces."""
import json
import sys
from pathlib import Path
import bpy


def prepare():
    reference=next(image for image in bpy.data.images if image.name.startswith('REFERENCE UTILISATEUR'))
    editors=0
    for window in bpy.context.window_manager.windows:
        window.workspace=bpy.data.workspaces['Layout']
        for area in window.screen.areas:
            if area.type=='IMAGE_EDITOR':
                area.spaces.active.image=reference
                region=next(region for region in area.regions if region.type=='WINDOW')
                with bpy.context.temp_override(window=window,area=area,region=region):
                    bpy.ops.image.view_all(fit_view=True)
                editors+=1
    assert editors,'The reference image editor is missing'
    if '--prepare-reference-layout' in sys.argv:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
        report=dict(reference_displayed=True,editors=editors,file=bpy.data.filepath)
        out=Path(bpy.data.filepath).parent/'verification/reference-rebord/layout-validation.json'
        out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return None


bpy.app.timers.register(prepare,first_interval=.3)

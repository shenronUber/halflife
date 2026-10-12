"""Produce the small Studio hook against the existing, pinned engine patch."""
import difflib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
path=root/'runtime/engine-source/ref/gl/gl_studio.c'
before=path.read_text(encoding='utf-8')
assert 'R_VFDrawFirstPersonBody' not in before
after=before.replace('void R_DrawViewModel( void )','static void R_VFDrawFirstPersonBody( void );\n\nvoid R_DrawViewModel( void )',1)
old='\tif( r_drawviewmodel->value == 0 )\n\t\treturn;\n\n'
# This check occurs both in events and rendering; only change the render block.
head,body=after.split('void R_DrawViewModel( void )',1)
assert old in body;body=body.replace(old,'',1)
needle='\ttr.blend = CL_FxBlend( view ) / 255.0f;'
assert needle in body
body=body.replace(needle,'\tR_VFDrawFirstPersonBody();\n\tif( r_drawviewmodel->value == 0 ) return;\n\n'+needle,1)
after=head+'void R_DrawViewModel( void )'+body
needle='static void R_StudioSubmitMesh( short *ptricmds, vec3_t *pstudionorms, float s, float t, float shellscale, int tesslevel )\n{'
assert needle in after
after=after.replace(needle,'static qboolean R_VFDrawBodyMesh( short *ptricmds, vec3_t *normals, float s, float t );\n\n'+needle+'\n\tif( R_VFDrawBodyMesh( ptricmds, pstudionorms, s, t )) return;',1)
patch='diff --git a/ref/gl/gl_studio.c b/ref/gl/gl_studio.c\n'+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/ref/gl/gl_studio.c',tofile='b/ref/gl/gl_studio.c'))
(root/'vector-fields/engine/first-person-body.patch').write_text(patch,encoding='utf-8',newline='\n')

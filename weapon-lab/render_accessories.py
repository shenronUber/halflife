"""Render textured accessory geometry for local inspection, without a game process."""
import base64,io,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'generated/accessories'
data=json.loads((OUT/'viewer-data.json').read_bytes())
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16)
def render(item,w=500,h=290):
 groups=[(np.frombuffer(base64.b64decode(g['vertices']),dtype='<f4').reshape(-1,8),np.array(Image.open(io.BytesIO(base64.b64decode(g['texture'].split(',')[1]))).convert('RGB')))for g in item['groups']]
 forward=np.array([0.82,-0.54,0.28]);forward/=np.linalg.norm(forward);right=np.cross([0,0,1],forward);right/=np.linalg.norm(right);up=np.cross(forward,right)
 R=np.array([right,up,forward]);allp=np.concatenate([v[:,:3]for v,t in groups]);c=(allp.max(0)+allp.min(0))/2
 view=(allp-c)@R.T;span=np.ptp(view[:,:2],axis=0);scale=min((w-65)/max(span[0],.01),(h-50)/max(span[1],.01))
 image=np.zeros((h,w,3),dtype=np.uint8);image[:]=[24,32,39];depth=np.full((h,w),-np.inf)
 for vs,tex in groups:
  for tri in vs.reshape(-1,3,8):
   p=(tri[:,:3]-c)@R.T;screen=np.column_stack([w/2+p[:,0]*scale,h/2-p[:,1]*scale]);x0,y0=np.maximum([0,0],np.floor(screen.min(0)).astype(int));x1,y1=np.minimum([w-1,h-1],np.ceil(screen.max(0)).astype(int))
   if x1<x0 or y1<y0:continue
   ax,ay=screen[0];bx,by=screen[1];cx,cy=screen[2];den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
   if abs(den)<1e-8:continue
   xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5);a=((by-cy)*(xx-cx)+(cx-bx)*(yy-cy))/den;b=((cy-ay)*(xx-cx)+(ax-cx)*(yy-cy))/den;cc=1-a-b
   z=a*p[0,2]+b*p[1,2]+cc*p[2,2];mask=(a>=0)&(b>=0)&(cc>=0)&(z>depth[y0:y1+1,x0:x1+1])
   if not mask.any():continue
   uv=a[...,None]*tri[0,6:8]+b[...,None]*tri[1,6:8]+cc[...,None]*tri[2,6:8]
   tx=np.clip((uv[...,0]*tex.shape[1]).astype(int),0,tex.shape[1]-1);ty=np.clip(((1-uv[...,1])*tex.shape[0]).astype(int),0,tex.shape[0]-1)
   normal=tri[:,3:6].mean(0);light=.72+.28*abs(np.dot(normal,[.3,-.4,.866]));rgb=np.minimum(255,tex[ty,tx]*light).astype(np.uint8)
   image[y0:y1+1,x0:x1+1][mask]=rgb[mask];depth[y0:y1+1,x0:x1+1][mask]=z[mask]
 return Image.fromarray(image)
if __name__=='__main__':
 canvas=Image.new('RGB',(1560,1590),(11,17,23));d=ImageDraw.Draw(canvas);d.text((25,18),'VECTOR FIELDS / Pièces extraites des modèles téléchargés',font=font,fill='#edf2ef');d.text((25,54),'Textures des créateurs conservées · échelles ajustées pour inspection · raccords en jeu à préparer',font=small,fill='#8fb8bc')
 for i,item in enumerate(data):
  im=render(item);dest=OUT/item['key']/'preview.png';im.save(dest)
  x=20+(i%3)*515;y=100+(i//3)*365;canvas.paste(im,(x,y));d.text((x,y+296),item['name'],font=font,fill='#edf2ef');d.text((x,y+328),str(item['triangles'])+' triangles · '+item['kind'],font=small,fill='#91a2b3')
 canvas.save(OUT/'contact-sheet.png')
 print(OUT/'contact-sheet.png')

"""Readable bone inventory and an anatomical guide for the R1 editor workshop."""
import csv,json
from pathlib import Path
import numpy as np
from studio_assets import Studio
ROOT=Path(__file__).resolve().parent
FINGERS=[('Pouce',[43,44,45],'#e99b29'),('Index',[47,48,49,50],'#488de7'),('Majeur',[51,52,53,54],'#53b681'),('Annulaire',[55,56,57,58],'#d781d0'),('Auriculaire',[59,60,61,62],'#56becb')]

def fp_labels():
 labels={'Bone01':'Origine du modèle','Bone02':'Repère de déplacement','Bone03':'Repère de placement','Bone04':'Ancrage commun des bras',
 'Bone05':'Coude / avant-bras droit','Bone06':'Articulation intermédiaire droite','Bone07':'Poignet / paume droite',
 'Bone08':'Pouce historique de prise d’arme (inactif sur le gant ouvert)','Bone09':'Pouce historique de prise d’arme (inactif sur le gant ouvert)','Bone10':'Pouce historique de prise d’arme (inactif sur le gant ouvert)',
 'Bone40':'Coude / avant-bras gauche','Bone41':'Articulation intermédiaire gauche','Bone42':'Poignet / paume gauche',
 'Bone75':'Repère de l’arme','Bone76':'Attache de l’arme','Bone71':'Attache du chargeur','R01_Bolt':'Attache de la culasse'}
 for finger,ids,_ in FINGERS:
  for side,prefix in [('gauche',''),('droit','VFRight_')]:
   for segment,num in enumerate(ids):
    role=('base','articulation suivante','articulation suivante','extrémité')[segment]
    labels[prefix+'Bone'+str(num)]=finger+' '+side+' : '+role+' ('+str(segment+1)+'/'+str(len(ids))+')'
 for num in [95,110,112,114,116,118,120]:labels['Bone'+str(num)]='Repère auxiliaire de manche / accessoire'
 return labels

def tp_label(name):
 if name in ['VF_Weapon','VF_Magazine','VF_Bolt']:return {'VF_Weapon':'Attache de l’arme','VF_Magazine':'Attache du chargeur','VF_Bolt':'Attache de la culasse'}[name]
 parts=name.replace('Bip01','').strip().split();side=''
 if parts and parts[0] in ['L','R']:side=' gauche'if parts.pop(0)=='L'else' droit'
 roles={'Pelvis':'Bassin','Leg':'Cuisse','Leg1':'Mollet','Foot':'Pied','Arm':'Clavicule','Arm1':'Bras','Arm2':'Avant-bras','Hand':'Poignet / main','Finger0':'Pouce simplifié','Finger1':'Doigts groupés : base','Finger11':'Doigts groupés : extrémité','Neck':'Cou','Head':'Tête'}
 key=' '.join(parts)
 return (roles.get(key,'Tronc : '+key if key.startswith('Spine')else'Origine du modèle')+side)

def catalog(model,view,folder):
 labels=fp_labels();rows=[];weighted=set();inherited=set()
 lines=(folder/'reference.smd').read_text(encoding='ascii').splitlines();start=lines.index('triangles')+1
 for offset,line in enumerate(lines[start:-1]):
  if offset%4:weighted.add(int(line.split()[0]))
 for bone in weighted:
  parent=model.parents[bone]
  while parent>=0:inherited.add(parent);parent=model.parents[parent]
 for i,name in enumerate(model.names):
  usage='Contrôle direct du mesh'if i in weighted else'Contrôle par les enfants'if i in inherited else'Aucun mesh visible'
  rows.append(dict(id=i,bone=name,role=labels.get(name,'Repère auxiliaire')if view=='first-person'else tp_label(name),parent=model.names[model.parents[i]]if model.parents[i]>=0 else '',usage=usage))
 (folder/'bones.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 with (folder/'bones.csv').open('w',encoding='utf-8-sig',newline='')as f:
  writer=csv.DictWriter(f,fieldnames=['id','bone','role','parent','usage'],delimiter=';');writer.writeheader();writer.writerows(rows)


def render(destination):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 rig=Studio(ROOT/'generated/traversal/r01_rig_tr.mdl');glove=Studio(ROOT/'generated/traversal/ledge_gloves.mdl')
 mapping={i:(i,rig.names.index(n))for i,n in enumerate(glove.names)}
 mesh=glove.mesh(target=rig.bind,mapping=mapping)
 fig,axes=plt.subplots(1,2,figsize=(13,8.5),facecolor='#141b26');fig.subplots_adjust(left=.04,right=.97,top=.87,bottom=.31,wspace=.16)
 for ax,side,wrist,prefix in [(axes[0],'Main gauche','Bone42',''),(axes[1],'Main droite','Bone07','VFRight_')]:
  hand=rig.names.index(wrist);inv=np.linalg.inv(rig.bind[hand]);allowed={hand}|{rig.names.index(prefix+'Bone'+str(b))for _,ids,_ in FINGERS for b in ids}
  polys=[];colors=[]
  for material,verts in mesh:
   if not all(v['b']in allowed for v in verts):continue
   polys.append([(inv@np.r_[v['p'],1])[:2]for v in verts]);uv=np.mean([v['uv']for v in verts],axis=0)
   _,w,h,pix,pal=glove.textures[material];u=int(np.clip(uv[0]*w,0,w-1));v=int(np.clip((1-uv[1])*h,0,h-1));index=pix[v*w+u]
   color=np.frombuffer(pal,dtype=np.uint8).reshape(256,3)[index]/255.;colors.append(color*.6+.18)
  ax.add_collection(PolyCollection(polys,facecolors=colors,edgecolors='#9baabb',linewidths=.12,zorder=1))
  for finger,ids,color in FINGERS:
   points=np.array([(inv@rig.bind[rig.names.index(prefix+'Bone'+str(b))])[:2,3]for b in ids])
   ax.plot(points[:,0],points[:,1],'-o',color=color,linewidth=2,markersize=4,zorder=3)
   for b,point in zip(ids,points):
    ax.annotate(str(b),point,xytext=(4,4),textcoords='offset points',color='white',fontsize=9,zorder=4)
  ax.plot(0,0,'o',color='#fff',markersize=5);ax.annotate(wrist,(0,0),xytext=(12,-12),textcoords='offset points',color='white',fontsize=11)
  ax.set_title(side+' — vue de la paume',color='white',fontsize=16,pad=15);ax.set_aspect('equal');ax.autoscale();ax.margins(.14);ax.axis('off');ax.set_facecolor('#141b26')
 fig.suptitle('R1 · repères des doigts dans fragMOTION',color='white',fontsize=21,y=.965)
 fig.text(.045,.91,'Géométrie réelle du gant. Pose de référence étendue, pas la suspension finale.',color='#bac7d9',fontsize=11)
 for i,(finger,ids,color)in enumerate(FINGERS):
  y=.26-i*.037
  fig.text(.065,y,finger,color=color,fontsize=12,weight='bold')
  fig.text(.205,y,' → '.join('Bone'+str(n)for n in ids),color='white',fontsize=11)
  fig.text(.63,y,'Droite : mêmes numéros, préfixe VFRight_',color='#bac7d9',fontsize=10)if i==0 else None
 fig.text(.065,.035,'Coudes / avant-bras : Bone40 gauche · Bone05 droit. Les noms doivent rester identiques lors de l’export.',color='#bac7d9',fontsize=10)
 fig.savefig(destination,dpi=130,facecolor=fig.get_facecolor());plt.close(fig)

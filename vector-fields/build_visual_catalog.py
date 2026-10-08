"""Name every local appearance and compile three shared meshes with skin families."""
import json,re,shutil
from pathlib import Path
import numpy as np
from PIL import Image
from build_modular import compile_model
import build_skins
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'generated/visual_skins'
NAMES={
 'soldier':'Bastion - soldat','hvyweapon':'Colosse - soutien lourd','scout':'Eclaireur',
 'civilian':'Diplomate','demo':'Sapeur','engineer':'Mecanicien','medic':'Secouriste',
 'pyro':'Incendiaire','sniper':'Sentinelle','spy':'Infiltrateur','barney':'Garde de securite',
 'gman':'Emissaire','hassassin':'Ombre','hgrunt':'Fantassin','holo':'Instructeur holographique',
 'islave':'Vortigaunt','bbbbarney':'Garde renforce','gina':'Gina','gordon':'Freeman',
 'helmet':'Casque bleu','ivan':'Ivan','recon':'Reconnaissance','robo':'Automate',
 'scientist':'Chercheur','skeleton':'Squelette','tmcm':'Combattant masque','zombie':'Contamine',
 'player':'Operateur','scientistu':'Chercheur civil','cleansuit_scientist':'Technicien etanche',
 'deadhaz':'Technicien sinistre','drill':'Instructeur militaire','gonome':'Gonome',
 'hgrunt_medic':'Medecin militaire','hgrunt_opfor':'Marine HECU','hgrunt_torch':'Soudeur HECU',
 'intro_commander':'Commandant','intro_medic':'Medecin de bord','intro_regular':'Fusilier de bord',
 'intro_saw':'Mitrailleur de bord','intro_torch':'Soudeur de bord','massn':'Commando noir',
 'otis':'Otis - gardien','pit_drone':'Drone de Xen','beret':'Beret vert','cl_suit':'Protection chimique',
 'ctf_barney':'Garde CTF','ctf_gina':'Gina CTF','ctf_gordon':'Freeman CTF','ctf_scientist':'Chercheur CTF',
 'fassn':'Assassin furtif','grunt':'Marine','recruit':'Recrue','shephard':'Shephard','tower':'Tour de garde',
 'recruit_push':'Recrue entrainement','strooper':'Soldat de choc','zombie_barney':'Garde contamine',
 'zombie_soldier':'Marine contamine','ba_holo':'Barney holographique','civ_coat_scientist':'Chercheur en manteau',
 'civ_paper_scientist':'Archiviste','civ_scientist':'Chercheur civil','console_civ_scientist':'Operateur de console',
 'dead_barney':'Garde blesse','gordon_scientist':'Freeman en laboratoire','gordon_suit':'Freeman HEV',
 'intro_barney':'Barney de service','intro_otis':'Otis de service','scientist_cower':'Chercheur accroupi',
 'wrangler':'Wrangler'}
DYES=[('Ardoise',(82,112,136)),('Cuivre',(152,84,48)),('Sable',(150,140,103))]

def main():
 manifest=json.loads((OUT/'skins.json').read_text());records=manifest['characters'];lines=[]
 for r in records:
  source=r['name'].lower();head=re.search(r' head (\d+)$',source);source=re.sub(r' head \d+$','',source)
  modern=source.endswith('2') and r['game']=='TFC';source=source[:-1] if modern else source
  label=NAMES.get(source,source.replace('_',' ').title())
  if modern:label+=' II'
  if head:label+=' / visage '+head[1]
  # A stable number distinguishes the NPC, multiplayer and expansion editions.
  r['display_name']=f'{r["game"]} / {label} #{r["id"]+1:03}'
  lines.append(f'{r["id"]}|{r["key"]}|{r["display_name"]}')
 families=[]
 for source,code,label in [(0,'bastion','Bastion'),(2,'eclaireur','Eclaireur'),(32,'hev','Operateur HEV')]:
  r=records[source];key='base_'+code;model='family_'+code
  # A shared archetype keeps its natural silhouette. Only the legacy donor
  # mix needs to be forced onto universal neck/waist profiles.
  build_skins.OUT=OUT
  build_skins.build_character(r,source,conform=False,key=key,export=False)
  materials=sorted({line.strip() for z in range(5) for line in (OUT/f'{key}_{z}.smd').read_text().splitlines() if line.lower().endswith('.bmp')})
  groups=[materials]
  for dye,(name,color) in enumerate(DYES,1):
   variants=[]
   for index,mat in enumerate(materials):
    im=Image.open(OUT/mat);palette=np.array(im.getpalette(),dtype=float).reshape(256,3)
    lum=palette@np.array([.2126,.7152,.0722]);chroma=palette.max(1)-palette.min(1)
    # Keep dark outlines and highlights; tint existing texels, never change UVs.
    target=np.array(color)/np.mean(color)*lum[:,None]
    weight=np.where((lum>35)&(lum<220),.7,.2)[:,None]
    result=np.clip(palette*(1-weight)+target*weight,0,255).astype(np.uint8)
    namebmp=f'{model}_{dye}_{index}.bmp';im.putpalette(result.reshape(-1).tolist());im.save(OUT/namebmp);variants.append(namebmp)
   groups.append(variants)
  qc=(OUT/(key+'.qc')).read_text().replace(f'"{key}.mdl"',f'"{model}.mdl"')
  qc+='\n$texturegroup skinfamilies\n{\n'+''.join('{ '+' '.join('"'+m+'"' for m in group)+' }\n' for group in groups)+'}\n'
  path=OUT/(model+'.qc');path.write_text(qc);compile_model(path)
  for skin,(name,_) in enumerate(DYES,1):
   id=len(lines);alias=f'style_{code}_{skin}';display=f'VF / {label} - {name}'
   lines.append(f'{id}|{alias}|{display}|2|{model}|{skin}')
   families.append(dict(id=id,key=alias,model=model,skin=skin,base=source,geometry_reference=key,display_name=display))
 manifest['families']=families
 (OUT/'skins.json').write_text(json.dumps(manifest,indent=2))
 (OUT/'skins.txt').write_text('\n'.join(lines)+'\n',encoding='ascii')
 print(f'PASS: {len(records)} named appearances + {len(families)} texture variants on 3 shared models')

if __name__=='__main__':main()

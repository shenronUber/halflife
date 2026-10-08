"""Export the six in-game budget emblems as reusable transparent SVGs."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parent
source=(ROOT.parent/'cl_dll/vf_ui.cpp').read_text()
entries=[('TED','Dissipation thermo-entropique','#f5a055'),('IP','Profil inertiel','#70b5f9'),('HS','Stabilisation harmonique','#c0a2fa'),('OI','Integrite operationnelle','#66dab4'),('SIG','Empreinte detectable','#5cd9e8'),('BIO','Charge metabolique','#9fdb73')]
out=ROOT/'assets/ui/budgets';out.mkdir(parents=True,exist_ok=True)
manifest=[]
for i,(code,name,color) in enumerate(entries):
 block=source.split(f' case {34+i}:',1)[1].split('break;',1)[0]
 shapes=[]
 for a,b,c,d in re.findall(r'L\((\d+),(\d+),(\d+),(\d+)\)',block):shapes.append(f'<path d="M{a} {b}L{c} {d}"/>')
 for a,b,c,d in re.findall(r'B\((\d+),(\d+),(\d+),(\d+)\)',block):shapes.append(f'<rect x="{a}" y="{b}" width="{c}" height="{d}" fill="{color}" stroke="none"/>')
 for a,b,c,d in re.findall(r'Frame\(x\+(\d+)\*k,y\+(\d+)\*k,(\d+)\*k,(\d+)\*k,c\)',block):shapes.append(f'<rect x="{a}" y="{b}" width="{c}" height="{d}"/>')
 assert shapes,code
 filename=code.lower()+'.svg'
 (out/filename).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" role="img"><title>{code} - {name}</title><g fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="square" stroke-linejoin="miter">'+''.join(shapes)+'</g></svg>\n')
 manifest.append({'code':code,'name':name,'system':'operator' if i>=4 else 'weapon','color':color,'icon':filename,'native_icon':34+i})
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('Exported six native budget emblems as SVG')

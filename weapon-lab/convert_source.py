"""Proof of Source -> GoldSrc conversion: textured meshes and sampled animations."""
import io,json,re,struct,subprocess,sys,hashlib,math
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent;sys.path.insert(0,str(PROJECT/'vector-fields'))
import build_modular as build
from studio_assets import Studio

def vtf(path):
 d=path.read_bytes();assert d[:4]==b'VTF\0';major,minor,head=struct.unpack_from('<3I',d,4);w,h=struct.unpack_from('<HH',d,16);frames=struct.unpack_from('<H',d,24)[0];fmt=struct.unpack_from('<I',d,52)[0];mips=d[56];low=struct.unpack_from('<I',d,57)[0];lw,lh=d[61:63];depth=struct.unpack_from('<H',d,63)[0] if minor>=2 else 1
 assert frames==1 and depth==1,'Animated/volume VTF needs separate conversion'
 def size(f,x,y):
  if f in (13,20):return max(1,(x+3)//4)*max(1,(y+3)//4)*8
  if f in (14,15):return max(1,(x+3)//4)*max(1,(y+3)//4)*16
  return x*y*({0:4,1:4,2:3,3:3,9:3,10:3,11:4,12:4,16:4}.get(f) or (_ for _ in ()).throw(ValueError('VTF format '+str(f))))
 offset=head+(size(low,lw,lh) if lw and lh else 0)
 if minor>=3:
  for i in range(struct.unpack_from('<I',d,68)[0]):
   typ,pos=struct.unpack_from('<II',d,80+8*i)
   if typ&0xffffff==0x30:offset=pos
 offset+=sum(size(fmt,max(1,w>>i),max(1,h>>i)) for i in range(1,mips))
 raw=d[offset:offset+size(fmt,w,h)];assert len(raw)==size(fmt,w,h)
 if fmt in (13,14,15,20):
  four={13:b'DXT1',20:b'DXT1',14:b'DXT3',15:b'DXT5'}[fmt]
  header=struct.pack('<7I',124,0x81007,h,w,len(raw),0,1)+bytes(44)+struct.pack('<II4s5I',32,4,four,0,0,0,0,0)+struct.pack('<5I',0x1000,0,0,0,0)
  im=Image.open(io.BytesIO(b'DDS '+header+raw)).convert('RGBA')
 else:
  mode={0:'RGBA',1:'ABGR',2:'RGB',3:'BGR',9:'RGB',10:'BGR',11:'ARGB',12:'BGRA',16:'BGRX'}[fmt]
  im=Image.frombytes('RGBA' if len(mode)==4 else 'RGB',(w,h),raw,'raw',mode).convert('RGBA')
 return im

def main():
 src=ROOT/'generated/source-test';pack=ROOT/'extracted/210349';out=ROOT/'generated/source-goldsrc';out.mkdir(exist_ok=True)
 qc=(src/'v_rif_m4a1.qc').read_text(encoding='utf-8');cds=[s.replace('\\','/').lower() for s in re.findall(r'\$cdmaterials\s+"([^"]+)"',qc)]
 vmts=list(pack.rglob('*.vmt'));vtfs=list(pack.rglob('*.vtf'));materials={};borrowed=[];meshes=[];weighted=0
 for smdname in re.findall(r'\bstudio\s+"([^"]+\.smd)"',qc):
  lines=(src/smdname).read_text(encoding='utf-8-sig').splitlines();lines=[l for l in lines if not l.startswith('//')];start=lines.index('triangles');header=lines[:start];tris=[]
  for i in range(start+1,len(lines)-1,4):
   mat=lines[i].strip()
   if mat not in materials:
    candidates=[p for p in vmts if p.stem.lower()==mat.lower() and any(('/materials/'+c) in p.as_posix().lower() for c in cds)]
    candidates.sort(key=lambda p:('Required'not in p.parts,len(str(p))))
    tex=None
    if candidates:
     vmt=candidates[0];text=vmt.read_text(errors='replace');m=re.search(r'"?\$basetexture"?\s+"?([^"\s]+)',text,re.I)
     if m:
      tail='/materials/'+m[1].replace('\\','/').lower()+'.vtf';ts=[p for p in vtfs if p.as_posix().lower().endswith(tail)];ts.sort(key=lambda p:('Required'not in p.parts,len(str(p))));tex=ts[0]if ts else None
    if tex is None and mat.lower()=='v_hands':
     tex=next((ROOT/'extracted/635773').rglob('v_hands.vtf'));borrowed.append(str(tex.relative_to(ROOT)))
    if tex is None:raise ValueError('Missing material '+mat)
    image=vtf(tex);image.thumbnail((512,512),Image.Resampling.LANCZOS);name=f'tex_{len(materials):02}.bmp';image.convert('RGB').quantize(colors=256).save(out/name)
    materials[mat]=dict(name=name,source=str(tex.relative_to(ROOT)),dimensions=image.size)
   rows=[]
   for row in lines[i+1:i+4]:
    f=row.split()
    if len(f)>9 and int(f[9])>0:
     weights=[(float(f[11+j*2]),int(f[10+j*2]))for j in range(int(f[9]))];f[0]=str(max(weights)[1]);weighted+=len(weights)>1
    rows.append(' '.join(f[:9]))
   parsed=[row.split()for row in rows]
   # Source UVs may use repeated tiles; GoldSrc's compiler crops outside [0,1].
   for axis in (7,8):
    shift=math.floor(min(float(row[axis])for row in parsed))
    for row in parsed:row[axis]=str(float(row[axis])-shift)
   rows=[' '.join(row)for row in parsed]
   tris.append((materials[mat]['name'],rows))
  for n in range(0,len(tris),1500):
   key=f'mesh_{len(meshes):02}';build.write_smd(out/(key+'.smd'),header,tris[n:n+1500]);meshes.append(key)
 sequences=[]
 for m in re.finditer(r'\$sequence\s+"([^"]+)"\s*\{([\s\S]*?)(?=\n\$sequence|\Z)',qc):
  name,body=m.groups();file=re.search(r'"([^"]+\.smd)"',body);fps=re.search(r'\bfps\s+([\d.]+)',body)
  if not file:continue
  text=(src/file[1].replace('\\','/')).read_text(encoding='utf-8-sig');text='\n'.join(l.strip()for l in text.splitlines()if not l.startswith('//'))+'\n';(out/(name+'.smd')).write_text(text,encoding='ascii');sequences.append((name,float(fps[1])if fps else 30))
 text='$modelname "source_m4.mdl"\n$cd "."\n$cdtexture "."\n$origin 0 0 0 0\n'
 for key in meshes:text+=f'$body "{key}" "{key}"\n'
 for name,fps in sequences:text+=f'$sequence "{name}" "{name}" fps {fps}'+(' loop'if'idle'in name else'')+'\n'
 for m in re.finditer(r'\$attachment\s+"\d+"\s+"([^"]+)"\s+([\d. -]+)',qc):text+=f'$attachment 0 "{m[1]}" {m[2].strip()}\n';break
 path=out/'source_m4.qc';path.write_text(text,encoding='ascii');model=build.compile_model(path);s=Studio(model)
 report=dict(source='https://gamebanana.com/mods/210349',source_version=44,target_version=10,output=str(model.relative_to(ROOT)),triangles=len(s.mesh()),bones=len(s.names),sequences=s.sequences,materials=materials,borrowed_hands=borrowed,weighted_vertices_collapsed=weighted,limitations=['Normal maps, reflection shaders and Source-specific animation events omitted','Multi-weight vertices assigned to strongest bone','Textures reduced to maximum 512 and 256 colors','Hand texture borrowed from the archived Old School CSS pack','In-game visual validation required'])
 (out/'conversion.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:report[k]for k in ['triangles','bones','sequences','weighted_vertices_collapsed']}))
if __name__=='__main__':main()

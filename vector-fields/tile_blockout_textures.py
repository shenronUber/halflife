"""Small native WAD3 of grid colours and movement markings; no downloaded art."""
import struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

COLOURS={'VX_FLOOR':(68,78,88),'VX_WALL':(185,91,39),'VX_COVER':(112,126,139),
 'VX_RUN':(35,168,186),'VX_SLIDE':(126,73,178),'VX_LEDGE':(218,173,43),
 'VX_PORT':(63,160,106),'VX_VOID':(155,50,47),'VX_WHITE':(190,193,192),
 'VX_COLD':(75,121,151),'VX_OPEN':(182,116,60),'VX_LEVEL':(153,131,60),'VX_DUCT':(111,86,137)}
LABELS={'VX_RUN':'WALL RUN  >>>','VX_SLIDE':'GLISSADE','VX_LEDGE':'CORNICHE',
 'VX_PORT':'ACCES','VX_VOID':'VIDE','VX_COLD':'FROID / SAS','VX_OPEN':'CHANTIER',
 'VX_LEVEL':'GALERIES','VX_DUCT':'CONDUITS'}

def write(path):
    font=ImageFont.load_default(size=12); lumps=[]
    for name,colour in COLOURS.items():
        palette=[colour,tuple(round(v*.66)for v in colour),(232,231,217),tuple(min(255,round(v*1.2))for v in colour)]
        palette += [(0,0,0)]*(256-len(palette))
        image=Image.new('P',(128,128)); image.putpalette([v for c in palette for v in c]); draw=ImageDraw.Draw(image)
        for n in (0,64,127):draw.line((n,0,n,127),fill=1,width=2);draw.line((0,n,127,n),fill=1,width=2)
        if name in LABELS:
            label=LABELS[name]; bounds=draw.textbbox((0,0),label,font=font)
            draw.rectangle((2,47,125,77),fill=1)
            draw.text(((128-(bounds[2]-bounds[0]))//2,53),label,fill=2,font=font)
        if name=='VX_PORT':draw.polygon([(45,88),(83,88),(83,98),(99,98),(64,119),(29,98),(45,98)],fill=2)
        if name=='VX_VOID':
            for x in range(-128,128,24):draw.polygon([(x,0),(x+12,0),(x+140,128),(x+128,128)],fill=1)
        data=[]; offsets=[]; offset=40
        for size in (128,64,32,16):
            mip=image.resize((size,size),Image.Resampling.NEAREST); offsets.append(offset)
            data.append(mip.tobytes()); offset+=size*size
        lump=struct.pack('<16s6I',name.encode(),128,128,*offsets)+b''.join(data)+struct.pack('<H',256)+bytes(v for c in palette for v in c)+b'\0\0'
        lumps.append((name,lump))
    body=bytearray(); directory=[]
    for name,lump in lumps:
        directory.append(struct.pack('<iiiBBBB16s',12+len(body),len(lump),len(lump),0x43,0,0,0,name.encode()))
        body.extend(lump)
    Path(path).write_bytes(struct.pack('<4sii',b'WAD3',len(lumps),12+len(body))+body+b''.join(directory))

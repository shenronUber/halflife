"""Assemble actual Blender renders into labelled inspection sheets."""
import argparse
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path)
args=parser.parse_args();folder=args.folder
report=json.loads((folder/'rig-audit.json').read_text(encoding='utf-8'))
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
records=report['renders'];outputs=[]
for key in report['tracks']:
    rows=[[r for r in records if r['track']==key and r['view']==view]for view in ('jeu','controle')]
    if not rows[0]:continue
    count=len(rows[0]);w=480*count;h=800
    sheet=Image.new('RGB',(w,h),(22,28,36));draw=ImageDraw.Draw(sheet)
    draw.text((12,8),f"{report['view']} / {key}",fill='white',font=font)
    for row,images in enumerate(rows):
        for col,r in enumerate(images):
            tile=Image.open(r['path']).convert('RGB')
            sheet.paste(tile,(col*480,44+row*384))
            draw.text((col*480+10,406+row*384),f"{r['view']} / {r['fraction']*100:.0f}%",fill=(220,226,232),font=small)
    path=folder/(key+'-planche.jpg');sheet.save(path,quality=94);outputs.append(str(path))
# One compact page per eight static angle poses makes every sector reviewable.
static=[key for key in report['tracks'] if report['tracks'][key]['frames']==3]
for page in range(0,len(static),8):
    keys=static[page:page+8];sheet=Image.new('RGB',(1440,3*384),(22,28,36));draw=ImageDraw.Draw(sheet)
    for index,key in enumerate(keys):
        r=next(r for r in records if r['track']==key and r['view']=='controle')
        tile=Image.open(r['path']).convert('RGB');x=index%3*480;y=index//3*384
        sheet.paste(tile,(x,y));draw.text((x+8,y+362),key,fill='white',font=small)
    path=folder/f'secteurs-{page//8+1:02d}.jpg';sheet.save(path,quality=94);outputs.append(str(path))
(folder/'contact-sheets.json').write_text(json.dumps(outputs,indent=2),encoding='utf-8')
print('SHEETS',len(outputs))

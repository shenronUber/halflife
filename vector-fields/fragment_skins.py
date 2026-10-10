"""Independent clothing/detail finishes through native Studio skin-table references."""
import struct
from pathlib import Path

FINISH_COUNT=14
DETAIL_MATERIAL='fragment_detail_original.bmp'

def skin_pairs(count=FINISH_COUNT):
    # Keep the historical uniform families 0..13 stable, then add mixed pairs.
    return [(i,i) for i in range(count)]+[(a,b) for a in range(count) for b in range(count) if a!=b]

def pair_skin(primary,detail,count=FINISH_COUNT):
    if not (0<=primary<count and 0<=detail<count):raise ValueError('Invalid fragment finish')
    return primary if primary==detail else count+primary*(count-1)+detail-(detail>primary)

def expand_skin_table(data,count=FINISH_COUNT):
    """Append references to the two compiled atlas banks; geometry/pixels stay intact.

    The classic compiler accepts only 32 QC rows. Compile 14 uniform families,
    then express all 196 pairs in the MDL's ordinary skin table, without new atlases.
    """
    result=bytearray(data)
    if result[:4]!=b'IDST' or struct.unpack_from('<i',result,4)[0]!=10:raise ValueError('Studio v10 model required')
    refs,families,offset=struct.unpack_from('<iii',result,192)
    if families!=count or refs<2:raise ValueError('Uniform fragment families required')
    textures,texture_offset=struct.unpack_from('<ii',result,180)
    names=[result[texture_offset+i*80:texture_offset+i*80+64].split(b'\0')[0].decode('ascii') for i in range(textures)]
    rows=[list(struct.unpack_from('<'+'h'*refs,result,offset+i*refs*2)) for i in range(count)]
    slots=[i for i,t in enumerate(rows[0]) if names[t]==DETAIL_MATERIAL]
    if len(slots)!=1:raise ValueError('One independent detail material required')
    detail=slots[0];combined=[]
    for primary,secondary in skin_pairs(count):
        row=rows[primary].copy();row[detail]=rows[secondary][detail];combined.extend(row)
    start=len(result);result.extend(struct.pack('<'+'h'*len(combined),*combined))
    struct.pack_into('<iii',result,192,refs,count*count,start)
    struct.pack_into('<i',result,72,len(result))
    return bytes(result)

def expand_file(path):
    path=Path(path);path.write_bytes(expand_skin_table(path.read_bytes()))

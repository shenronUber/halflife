"""Download selected model archives and extract them into isolated directories."""
import concurrent.futures
import hashlib
import json
import subprocess
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parent
def safe_member(name, destination):
    relative=PurePosixPath(name.replace('\\','/'))
    if relative.is_absolute() or '..' in relative.parts or ':' in name:
        raise ValueError(f'Unsafe archive path: {name}')
    return destination.joinpath(*relative.parts)

def download(record):
    item_id=record['id']
    f=next(f for f in record['files'] if not f.get('_bIsArchived',False))
    archive=ROOT/'downloads'/f'{item_id}-{f["_sFile"]}'
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists():
        request=urllib.request.Request(f['_sDownloadUrl'],headers={'User-Agent':'VectorFields-local-asset-study/0.1'})
        with urllib.request.urlopen(request,timeout=90) as response, archive.open('wb') as out:
            while chunk:=response.read(1024*1024): out.write(chunk)
    raw=archive.read_bytes()
    assert len(raw)==f['_nFilesize'], f'Incomplete archive: {archive}'
    if f.get('_sMd5Checksum'):
        assert hashlib.md5(raw).hexdigest()==f['_sMd5Checksum'].lower(), f'Checksum mismatch: {archive}'
    destination=ROOT/'extracted'/str(item_id)
    destination.mkdir(parents=True,exist_ok=True)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                path=safe_member(member.filename,destination)
                if member.is_dir(): continue
                if member.external_attr>>16 & 0o170000 == 0o120000:
                    raise ValueError('Archive contains a symlink')
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(z.read(member))
    else:
        sevenzip=ROOT/'tools'/'7zip'/'7z.exe'
        if sevenzip.exists():
            listing=subprocess.check_output([str(sevenzip),'l','-slt','-sccUTF-8',str(archive)],text=True,encoding='utf-8',errors='strict')
            if '\n----------\n' not in listing:
                raise ValueError('Cannot validate archive listing')
            entries=listing.split('\n----------\n',1)[1]
            for block in entries.split('\n\n'):
                fields=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
                if 'Path' not in fields:continue
                safe_member(fields['Path'],destination)
                if any('link' in k.lower() or 'reparse' in k.lower() for k in fields):
                    raise ValueError('Archive contains links')
                if any(v.startswith(('l','h')) for v in fields.get('Attributes','').split()):
                    raise ValueError('Archive contains links')
        else:
            listing=subprocess.check_output(['tar','-tf',str(archive)],text=True,encoding='utf-8',errors='replace')
            for name in listing.splitlines():safe_member(name,destination)
            detailed=subprocess.check_output(['tar','-tvf',str(archive)],text=True,encoding='utf-8',errors='replace')
            if any(line.startswith(('l','h')) for line in detailed.splitlines()):
                raise ValueError('Archive contains links')
        unrar=Path('C:/Program Files/WinRAR/UnRAR.exe')
        if sevenzip.exists():
            subprocess.run([str(sevenzip),'x',str(archive),'-o'+str(destination),'-y','-bso0'],check=True)
        elif unrar.exists():
            subprocess.run([str(unrar),'x','-o+','-idq',str(archive),str(destination)+'\\'],check=True)
        else:
            subprocess.run(['tar','-xf',str(archive),'-C',str(destination)],check=True)
    result={'id':item_id,'name':record['name'],'archive':str(archive.relative_to(ROOT)),
            'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
            'models':[str(p.relative_to(ROOT)) for p in destination.rglob('*') if p.suffix.lower()=='.mdl']}
    print(f'{item_id}: {record["name"]} | {len(result["models"])} models',flush=True)
    return result

if __name__=='__main__':
    records=json.loads((ROOT/'catalog'/'selection.json').read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(download,records))
    (ROOT/'catalog'/'downloads.json').write_text(json.dumps(results,indent=2),encoding='utf-8')

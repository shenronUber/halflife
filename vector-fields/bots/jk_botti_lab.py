"""Reproducible local jk_botti smoke test; uses an isolated, prepared runtime."""
import argparse,json,re,socket,subprocess,time,sys,struct,hashlib,gzip,math
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[2]
ROOT=PROJECT/'runtime/jk-botti-research'
ENGINE=ROOT/'engine';MOD=ENGINE/'valve'
STEAM=Path('F:/SteamLibrary/steamapps/common/Half-Life')
PORT=27035
PASSWORD='vf_bot_local_test'
class Server:
    def __init__(self,mapname,logname):
        self.log=ENGINE/logname
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as check:
            check.bind(('127.0.0.1',PORT))
        self.p=subprocess.Popen([str(ENGINE/'xash.exe'),'-rodir',str(STEAM),'-game','valve','-console','-noip6','-log',logname,'+ip','127.0.0.1','-port',str(PORT),'+maxplayers','6','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+developer','1','+rcon_password',PASSWORD,'+map',mapname,'+exec','vf_voice_behavior.cfg'],cwd=ENGINE,creationflags=subprocess.CREATE_NO_WINDOW)
        self.responses=[]
    def command(self,cmd):
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.settimeout(1)
        sock.sendto(b'\xff\xff\xff\xffrcon '+PASSWORD.encode()+b' '+cmd.encode()+b'\n\0',('127.0.0.1',PORT))
        chunks=[]
        try:
            while True:
                p=sock.recv(65535)
                if p.startswith(b'\xff\xff\xff\xffprint\n'):p=p[10:]
                chunks.append(p.rstrip(b'\0').decode('latin1'));sock.settimeout(.12)
        except (socket.timeout,ConnectionResetError):pass
        finally:sock.close()
        out=''.join(chunks);self.responses.append({'command':cmd,'output':out});return out
    def ready(self):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            if self.p.poll() is not None:raise RuntimeError(f'Server exited {self.p.returncode}: {self.log}')
            if 'map:' in self.command('status'):return
            time.sleep(.3)
        raise RuntimeError('Server failed to become ready: '+str(self.log))
    def probe(self):
        return [json.loads(m) for m in re.findall(r'VFBOT (\{[^\r\n]+\})',self.command('vf_bot_probe'))]
    def close(self):
        if self.p.poll() is None:
            self.command('quit')
            try:self.p.wait(4)
            except subprocess.TimeoutExpired:self.p.terminate();self.p.wait(5)
def smoke(mapname,seconds=25,duel=False):
    server=Server(mapname,'jk-'+mapname+'.log');samples=[]
    try:
        server.ready();time.sleep(5)
        if duel:
            sys.path.insert(0,str(PROJECT/'vector-fields'))
            from import_tfc import entities
            spawns=[e for e in entities((MOD/'maps'/(mapname+'.bsp')).read_bytes()) if e.get('classname')=='info_player_deathmatch'][:2]
            positions=[list(map(float,e['origin'].split())) for e in spawns]
            if len(positions)!=2:raise RuntimeError('Two deathmatch spawns required for controlled duel')
            for i,xyz in enumerate(positions,1):
                other=positions[2-i];yaw=math.degrees(math.atan2(other[1]-xyz[1],other[0]-xyz[0]))
                server.command('vf_bot_place %d %s %s %s %s'%(i,*xyz,yaw))
        print('PLUGINS',server.command('meta list').strip(),flush=True)
        for _ in range(max(2,int(seconds/3))):
            samples.append({'time':time.time(),'players':server.probe()});time.sleep(3)
        players=samples[-1]['players'];assert len([p for p in players if p['fake']])==2,players
        report={'map':mapname,'controlled_duel':duel,'seconds':seconds,'samples':samples,'responses':server.responses,'log':str(server.log),'exit':server.p.poll()}
        if duel:assert sum(p['mp5_shots'] for p in players)>0,players
        (ROOT/('test-'+mapname+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('RESULT',mapname,json.dumps(players),flush=True)
    finally:server.close()
    assert server.p.returncode==0,server.p.returncode
    return report

def audit():
    sys.path.insert(0,str(PROJECT/'vector-fields'))
    from import_tfc import entities
    stocks={p.stem:struct.unpack_from('<4i',gzip.decompress(p.read_bytes()),8)[3] for p in (ROOT/'package/addons/jk_botti/waypoints').glob('*.wpt')}
    rows=[]
    for folder,kind in [(PROJECT/'runtime/vector-engine/vf_visual/maps','project'),(STEAM/'valve/maps','half-life')]:
        for p in sorted(folder.glob('*.bsp')):
            data=p.read_bytes();version=struct.unpack_from('<i',data)[0]
            if version!=30:rows.append({'map':p.stem,'family':kind,'format':version});continue
            items=entities(data);classes={}
            for e in items:c=e.get('classname','');classes[c]=classes.get(c,0)+1
            family='tfc' if p.stem.startswith('vf_tfc_') else 'cs' if p.stem.startswith('vf_cs_') else kind
            rows.append({'map':p.stem,'family':family,'format':version,'sha256':hashlib.sha256(data).hexdigest(),'source':str(p),'deathmatch_spawns':classes.get('info_player_deathmatch',0),'team_spawns':classes.get('info_player_teamspawn',0)+classes.get('i_p_t',0),'single_spawns':classes.get('info_player_start',0),'stock_waypoints':stocks.get(p.stem,0),'weapon_entities':sum(n for c,n in classes.items() if c.startswith('weapon_')),'classes':classes})
    report={'jk_botti':'1.62','stock_waypoints':stocks,'maps':rows}
    (ROOT/'map-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('MAP AUDIT',json.dumps([{k:r[k] for k in ('map','family','deathmatch_spawns','team_spawns','stock_waypoints')} for r in rows if r.get('family') in ('cs','tfc') or r.get('stock_waypoints')]),flush=True)
    return report
def play(mapname):
    from prepare_jk_botti import sync_voice_runtime
    sync_voice_runtime(ENGINE)
    if not re.fullmatch(r'[A-Za-z0-9_]+',mapname):raise ValueError('Invalid map name')
    if not any((folder/(mapname+'.bsp')).is_file() for folder in (MOD/'maps',STEAM/'valve/maps')):raise FileNotFoundError(mapname)
    controls='exec lab_controls.cfg\nrcon_password '+PASSWORD+'\nbind F4 "rcon changelevel vf_range"\nbind F5 "rcon changelevel crossfire"\n'
    (MOD/'vf_bot_controls.cfg').write_text(controls,encoding='ascii')
    server=Server(mapname,'jk-play-server.log');client=None
    try:
        server.ready()
        client=subprocess.Popen([str(ENGINE/'xash3d.exe'),'-rodir',str(STEAM),'-game','valve','-borderless','-width','1920','-height','1080','-nointro','-log','jk-play-client.log','-clientport','27036','+name','VF_Player','+exec','vf_bot_controls.cfg','+connect',f'127.0.0.1:{PORT}'],cwd=ENGINE)
        client.wait()
        if client.returncode:raise RuntimeError('Client exited: '+str(client.returncode))
    finally:
        if client is not None and client.poll() is None:client.terminate();client.wait(5)
        server.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['audit','smoke','play']);parser.add_argument('--map',default='vf_range');parser.add_argument('--seconds',type=int,default=25);parser.add_argument('--duel',action='store_true');args=parser.parse_args()
    if args.action=='audit':audit()
    elif args.action=='play':play(args.map)
    else:smoke(args.map,args.seconds,args.duel)

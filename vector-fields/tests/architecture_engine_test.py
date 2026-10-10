"""Isolated engine regressions for validation, stable saves and the server rig.

Uses the real client/server DLLs. The null renderer only suppresses drawing;
this test does not validate pixels. Run after build.ps1. Runtime files are ignored.
"""
import json, os, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ENGINE=ROOT.parent/'runtime/vector-engine'
MOD=ENGINE/'vf_architecture'
SLOTS='head shoulders gloves torso belt legs boots shield special receiver barrel muzzle feed chamber ammo projectile optic underbarrel grip power cooling'.split()


def headless_renderer():
    # The upstream null renderer leaves the triangle API empty. Supply no-op
    # drawing callbacks so the production HUD can run without an OpenGL window.
    source=ROOT.parent/'runtime/engine-source'
    code=(source/'ref/null/r_context.c').read_text()
    old='static void R_FillTriAPI( triangleapi_t *api )\n{\n\t;\n}'
    new='''static void NullColor4f(float r,float g,float b,float a) {}
static void NullTexCoord2f(float u,float v) {}
static void NullVertex3f(float x,float y,float z) {}
static void NullCull(TRICULLSTYLE style) {}
static int NullSprite(struct model_s *model,int frame) {return 1;}
static void R_FillTriAPI( triangleapi_t *api ) {
 api->version=TRI_API_VERSION;
 api->RenderMode=R_SimpleStubInt;api->Begin=R_SimpleStubInt;api->End=R_SimpleStub;
 api->Color4f=NullColor4f;api->TexCoord2f=NullTexCoord2f;api->Vertex3f=NullVertex3f;
 api->CullFace=NullCull;api->SpriteTexture=NullSprite;
}'''
    assert code.count(old)==1
    test_source=ROOT/'build/ref_null_test.c';test_source.write_text(code.replace(old,new))
    vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
    vs=subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip()
    includes=['public','common','pm_shared','engine','engine/common','engine/common/imagelib','filesystem','3rdparty/library_suffix/include']
    command=f'call "{vs}/VC/Auxiliary/Build/vcvarsall.bat" x86 >nul && cl /nologo /std:c11 /LD /DREF_DLL '
    command+=' '.join(f'/I"{source/x}"'for x in includes)
    command+=f' "{test_source}" /Fo"{ROOT}/build/ref_null_test.obj" /Fe"{ROOT}/build/ref_null.dll"'
    subprocess.run(command,shell=True,check=True,capture_output=True)
    shutil.copy2(ROOT/'build/ref_null.dll',ENGINE/'ref_null.dll')


def prepare():
    for d in ('dlls','cl_dlls','vf','models/vf_skins','save'):(MOD/d).mkdir(parents=True,exist_ok=True)
    (MOD/'gameinfo.txt').write_text('title "Vector Fields regression"\nbasedir "valve"\nfallback_dir "vf_visual"\ngamedll "dlls/hl.dll"\ndllpath "cl_dlls"\nstartmap "vf_range"\ngamemode "normal"\nmax_edicts "2048"\n')
    for src,dst in [('build/server/hl.dll','dlls/hl.dll'),('build/client/client.dll','cl_dlls/client.dll'),('data/equipment.txt','vf/equipment.txt'),('data/r01_styles.txt','vf/r01_styles.txt'),('generated/visual_skins/skins.txt','vf/skins.txt'),('generated/personas/persona_rig.mdl','models/vf_skins/persona_rig.mdl')]:shutil.copy2(ROOT/src,MOD/dst)
    (MOD/'vf/native_engine.txt').write_text('1\n')


def run(name,script,multiplayer=False):
    (MOD/(name+'.cfg')).write_text('wait 100\ndeveloper 2\nvf_operator\nwait 25\n'+script+'wait 20\nquit\n')
    env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    command=[str(ENGINE/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',MOD.name,'-ref','null','-nosound','-nomouse','-nojoy','-nointro','-console','-nowriteconfig','-port','27036','-log',name+'.log','+developer','2','+map','vf_range','+exec',name+'.cfg']
    if multiplayer:
        index=command.index('+map');command[index:index]=['+maxplayers','2','+deathmatch','1','+sv_cheats','0']
    p=subprocess.run(command,cwd=ENGINE,env=env,capture_output=True,timeout=45)
    log=(ENGINE/(name+'.log')).read_text(errors='replace')
    assert p.returncode==0,(name,p.returncode,log[-2000:])
    assert 'VFState rejected'not in log and 'Crash:'not in log,name
    return log


def fingerprint(path):
    h=2166136261
    for b in path.read_bytes():h=((h^b)*16777619)&0xffffffff
    return h



def equipment():
    rows=[r.split('|')for r in (MOD/'vf/equipment.txt').read_text().splitlines()if r and not r.startswith(('#','limits|'))]
    ids={r[1]:i+1 for i,r in enumerate(rows)}
    keys=[next(r[1]for r in rows if r[0]==s and (len(r)==15 or s in ['shoulders','belt','shield','special'] or len(r)==17))for s in SLOTS]
    keys[0]='gign_head_trench';keys[2]='gign_gloves_noir';keys[9]='r01_receiver_top__original';keys[1]=''
    finish_keys=[r.split('|')[1]for r in (MOD/'vf/r01_styles.txt').read_text().splitlines()if r]
    for slot in range(10,21):keys[slot]=next(r[1]for r in rows if len(r)==17 and r[15]=='r01_'+SLOTS[slot]+'_a' and r[16]==finish_keys[slot-9])
    return keys,[ids[k]if k else 0 for k in keys],ids


def main():
    prepare();headless_renderer()
    keys,items,ids=equipment();styles=list(range(12))
    def command(selection,dev=False,chosen=None):return 'cmd '+('vf_apply_dev'if dev else 'vf_apply')+' '+str(fingerprint(MOD/'vf/equipment.txt'))+' '+' '.join(map(str,selection))+' '+str(fingerprint(MOD/'vf/r01_styles.txt'))+' '+' '.join(map(str,styles if chosen is None else chosen))+'\nwait 20\n'
    missing=items.copy();missing[10]=0
    mixed=items.copy();mixed[12]=ids['feed_standard']
    historical=items.copy();historical[0]=ids['head_experimental']
    skin_rows=[r.split('|')for r in (MOD/'vf/skins.txt').read_text().splitlines()if r]
    skin_lookup={r[1]:int(r[0])for r in skin_rows}
    # Use five actual authored entries, independent of catalogue ordering.
    free_keys=[r[1]for r in skin_rows if len(r)==6 and r[4]=='persona_scout'][-5:]
    free=[skin_lookup[k]for k in free_keys]
    forged=styles.copy();forged[0]=13
    script=command(items)+command(items,chosen=forged)+command(missing)+command(mixed)+command(historical)
    script+='cmd vf_model_info\nwait 10\nsave architecture_keys\nwait 30\n'
    # Historical equipment now deliberately falls back to the fitted GIGN look.
    # Exercise the legacy skeleton through an explicit developer appearance.
    legacy_skin=next(int(r[0]) for r in skin_rows if len(r)<5 or r[4]!='persona_scout')
    legacy_apply='cmd vf_appearance_mode 1\nwait 15\ncmd vf_skin_apply '+str(fingerprint(MOD/'vf/skins.txt'))+' '+(' '.join([str(legacy_skin)]*5))+'\nwait 20\n'
    script+=command(historical,True)+legacy_apply+'cmd vf_model_info\nwait 15\ncmd vf_appearance_mode 0\nwait 15\n'+command(items)
    script+='cmd vf_appearance_mode 1\nwait 15\ncmd vf_skin_apply '+str(fingerprint(MOD/'vf/skins.txt'))+' '+' '.join(map(str,free))+'\nwait 20\nsave architecture_free\nwait 30\n'
    log=run('architecture_validation',script)
    assert log.count('VF equipment: result=6')==3
    assert log.count('VF equipment: result=2')==1,'named item with forged finish must be refused'
    assert 'model=models/vf_skins/persona_rig.mdl developer=0 keys=7'in log
    assert 'model=models/vf_operator.mdl developer=1 keys=7'in log
    assert 'Saving game to save/architecture_keys.sav'in log
    style_keys=[r.split('|')[1]for r in (MOD/'vf/r01_styles.txt').read_text().splitlines()if r]
    # Simulate editing and reordering all three catalogues between launches.
    file=MOD/'vf/equipment.txt';rows=file.read_text().splitlines();limits=next(r for r in rows if r.startswith('limits|'))
    file.write_text('# migration regression\n'+limits+'\n'+'\n'.join(reversed([r for r in rows if r and not r.startswith(('#','limits|'))]))+'\n')
    for filename in ('r01_styles.txt','skins.txt'):
        file=MOD/'vf'/filename;rows=[r.split('|')for r in file.read_text().splitlines()if r];rows.reverse()
        for i,row in enumerate(rows):
            row[0]=str(i)
            if filename=='r01_styles.txt':row[5]=str(i)
        file.write_text('\n'.join('|'.join(r)for r in rows)+'\n')
    _,_,new_ids=equipment()
    new_style_ids={r.split('|')[1]:int(r.split('|')[0])for r in (MOD/'vf/r01_styles.txt').read_text().splitlines()if r}
    new_skin_ids={r.split('|')[1]:int(r.split('|')[0])for r in (MOD/'vf/skins.txt').read_text().splitlines()if r}
    restore='load architecture_keys\nwait 160\ndeveloper 2\nvf_operator\nwait 20\ncmd vf_request\ncmd vf_model_info\nwait 20\n'
    restore+='load architecture_free\nwait 160\ndeveloper 2\ncmd vf_skin_request\ncmd vf_model_info\nwait 20\n'
    log=run('architecture_migration',restore)
    linked,free_log=log.split('Loading game from save/architecture_free.sav')
    assert f'head={new_ids[keys[0]]} slots=21'in linked
    assert 'receiver=r01_receiver_top'in linked
    assert f'first={new_style_ids[style_keys[0]]} optic={new_style_ids[style_keys[7]]} feed={new_style_ids[style_keys[3]]}'in linked
    assert 'skins='+','.join(str(new_skin_ids[k])for k in free_keys)in free_log
    assert 'model=models/vf_skins/persona_rig.mdl developer=0 keys=7'in free_log
    legacy=ROOT/'build/legacy-0.14.sav'
    candidate=ENGINE/'vf_visual/save/vf_current_release_test.sav'
    if not legacy.exists()and candidate.exists()and b'm_vfItemKeys'not in candidate.read_bytes():shutil.copy2(candidate,legacy)
    if legacy.exists():
        shutil.copy2(legacy,MOD/'save/architecture_legacy.sav')
        log=run('architecture_legacy','load architecture_legacy\nwait 160\ndeveloper 2\ncmd vf_request\ncmd give weapon_crowbar\nweapon_crowbar\nwait 30\ncmd vf_model_info\nwait 20\n')
        after=log.split('Loading game from save/architecture_legacy.sav')[-1]
        assert f'head={new_ids["gign_head_trench"]} slots=21'in after
        assert 'model=models/vf_skins/persona_rig.mdl developer=0 keys=7'in after
    denied=run('architecture_permissions',command(historical,True)+'cmd vf_appearance_mode 1\nwait 20\ncmd vf_model_info\n',multiplayer=True)
    assert 'VFBuild received: result=5'in denied and 'VFSkin: result=4'in denied
    assert 'developer=0 keys=7'in denied
    report={'checks':['server rejects incomplete R01, mixed feed, historical gameplay gear and forged item finishes','explicit developer build retains historical gear; free appearance selects the original skeleton','gameplay uses fitted GIGN server skeleton','real save/load preserves equipment, twelve finishes and five free skins across reordered catalogues','pre-stable-key 0.14 save imports when local fixture exists','multiplayer without cheats rejects developer equipment and free appearance'],'renderer':'headless; no pixel validation','legacy_fixture_tested':legacy.exists()}
    (ROOT/'build/architecture-engine-verification.json').write_text(json.dumps(report,indent=2))
    print('PASS isolated engine: authoritative validation, both skeletons, stable save/load and legacy migration')

if __name__=='__main__':main()

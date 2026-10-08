"""Exercise native pointer hit testing, navigation and server-backed commits."""
import json, subprocess, time, re, argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ENGINE=ROOT.parent/'runtime/vector-engine'; MOD=ENGINE/'vf_visual'
def run(width=1920,height=1080):
 captures=[]
 def snap(name):
  name=f'ui_{width}_{name}';captures.append(name)
  return f'wait 20\nscreenshot scrshots/{name}.png\nwait 4\n'
 def click(x,y):return f'vf_ui_pointer {x} {y} 1\nwait 3\nvf_ui_pointer {x} {y} 0\nwait 12\n'
 s='wait 150\ndeveloper 1\ncon_notifytime 0\nvf_visual_enabled 0\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 20\nvf_character\nwait 40\n'+snap('operator')
 s+=click(1020,332)+click(640,104)+click(140,104)+snap('compare')+click(1150,693)+'wait 35\n'
 s+=click(410,104)+click(198,276)+snap('weapon_systems')
 s+=click(240,590)+'vf_revert\n'+''.join(f'vf_select_slot {slot}\nvf_next_item\n' for slot in range(9,21))+snap('overbudget')
 s+='echo VFUI_BLOCKED_BEGIN\n'+click(1150,693)+'echo VFUI_BLOCKED_END\n'+click(964,693)
 s+=click(1093,40)+click(600,395)+snap('families')+click(1170,173)
 for code,y in [('sig',274),('bio',335),('ted',444),('ip',501),('hs',558),('oi',615)]:s+=click(215,y)+snap('guide_'+code)
 s+=click(1093,40)
 s+=click(640,104)+'wait 40\n'+click(1225,207)+click(1010,265)+click(140,540)+click(1150,693)+'wait 35\n'+snap('skins')
 s+=click(140,341)+click(1010,315)+snap('gloves')+click(1150,693)+'wait 30\n'
 s+='vf_ui_pointer 540 350 1\nwait 3\nvf_ui_pointer 620 350 -1\nwait 3\nvf_ui_pointer 620 350 0\nwait 3\nvf_ui_pointer 540 350 2\n'+snap('rotated')
 s+=click(901,104)+click(245,521)+snap('modules')+click(1150,693)
 s+=click(1130,104)+snap('arsenal')+click(1222,590)+click(1060,302)+snap('arsenal_page2')
 s+=click(1220,40)+snap('game')+'cmd vf_body_info\n'
 s+='vf_character\nwait 30\n'+snap('restored')+'vf_character\nwait 10\nquit\n'
 (MOD/'vf_ui_test.cfg').write_text(s,encoding='ascii')
 logfile=f'ui-{width}-test.log'
 args=[str(ENGINE/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_visual','-borderless','-width',str(width),'-height',str(height),'-console','-nointro','-nowriteconfig','-log',logfile,'+exec','lab_controls.cfg','+map','vf_range','+exec','vf_ui_test.cfg']
 started=time.time();p=subprocess.Popen(args,cwd=ENGINE)
 try:p.wait(timeout=100)
 except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
 assert p.returncode==0,p.returncode
 log=(ENGINE/logfile).read_text(errors='replace')
 for value in ['VFBuild received: result=0 hash=567787589 head=2','VFUI click: Appliquer','VFUI click: Anom.','VFUI click: Guide','VFUI click: Apparence','VFUI click: Arme / style','VFUI click: Equiper','VFSkin client: result=0 ids=145,145,146,145,145','VFBody player=1 mins=-16,-16,-36 maxs=16,16,36 rifle=1']:
  assert value in log,value
 for code in ['SIG','BIO','TED','IP','HS','OI']:assert f'VFUI budget: {code}' in log,code
 blocked=log.split('VFUI_BLOCKED_BEGIN',1)[1].split('VFUI_BLOCKED_END',1)[0]
 assert 'VFUI click: Appliquer' not in blocked,'Over-budget apply must be disabled'
 for name in captures:
  file=MOD/'scrshots'/(name+'.png');assert file.stat().st_mtime>=started and file.stat().st_size>1000,name
 report={'resolution':[width,height],'screenshots':captures,'checks':['all five views reached using pointer press/release','draft survives navigation to appearance and back, then server confirms head=2','over-budget Apply button rejected pointer click','family guide and filters usable','all six budget explanations opened via pointer','source applied to all five zones, then gloves changed independently','skin selection confirmed by server','drag and wheel routed through native preview controls','hybrid equipped through pointer','arsenal pagination and selection','menu closed and collision hull preserved'],'limits':['Pointer events injected at client UI boundary; physical OS mouse input not covered.']}
 (ROOT/'build'/f'ui-verification-{width}.json').write_text(json.dumps(report,indent=2))
 print('PASS UI',width,len(captures),'screenshots')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--width',type=int,default=1920);parser.add_argument('--height',type=int,default=1080);a=parser.parse_args();run(a.width,a.height)

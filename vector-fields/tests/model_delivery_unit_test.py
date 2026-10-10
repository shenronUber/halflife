"""Model and delivery contracts fail safely without changing inventory identity."""
import json
import importlib.util
from unittest.mock import patch
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import model_contract as models
import release


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.data=models.load();self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)/'models.json'

    def load_modified(self):
        self.path.write_text(json.dumps(self.data));return models.load(self.path)

    def test_adding_top_chassis_updates_generated_selector(self):
        self.data['receivers']['r01_receiver_new']=dict(feed_mount='top')
        self.assertIn('{"r01_receiver_new", 2, false}',models.header(self.load_modified()))

    def test_invalid_feed_mount_is_rejected(self):
        self.data['receivers']['r01_receiver_top']['feed_mount']='front'
        with self.assertRaises(ValueError):self.load_modified()

    def test_unsafe_carrier_path_is_rejected(self):
        self.data['platforms'][0]['first_person']='models/../foreign.mdl'
        with self.assertRaises(ValueError):self.load_modified()

    def test_mount_wire_order_cannot_be_changed(self):
        self.data['platforms'].reverse()
        with self.assertRaises(ValueError):self.load_modified()

    def test_grip_trait_requires_boolean(self):
        self.data['underbarrels']['r01_underbarrel_a']['support_grip']='false'
        with self.assertRaises(ValueError):self.load_modified()

    def test_ambiguous_sockets_are_rejected(self):
        self.data['sockets']['first_person']['feed']=self.data['sockets']['first_person']['weapon']
        with self.assertRaises(ValueError):self.load_modified()

    def test_donor_joint_reordering_requires_explicit_review(self):
        names=self.data['skeletons']['first_person'].copy();names[10],names[12]=names[12],names[10]
        with self.assertRaisesRegex(ValueError,'joint mapping'):models.check_skeleton(names,'first_person',self.data)

    def test_added_bolt_does_not_change_source_joint_mapping(self):
        models.check_skeleton(self.data['skeletons']['first_person']+['R01_Bolt'],'first_person',self.data)

    def test_generated_header_matches_single_source(self):
        models.generate(check=True)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'source';self.dest=Path(self.temp.name)/'runtime';self.root.mkdir()
        for group,_,required in release.MODEL_GROUPS:
            for name in required:self.write('generated/'+group+'/'+name+'.mdl',b'model')
        self.write('generated/r01/manifest.json',json.dumps(dict(pieces=[dict(id='r01_receiver_a')])).encode())
        self.write('generated/r01/r01_receiver_a.mdl',b'receiver')
        for source in ['build/client/client.dll','build/server/hl.dll','data/equipment.txt','data/r01_styles.txt','generated/visual_skins/skins.txt','data/effects.json','data/weapon_fx.json','generated/weapon-fx/decals.wad','version.json','generated/effects/test.spr','generated/weapon-fx/sprites/test.spr','generated/weapon-fx/sound/test.wav']:
            self.write(source,b'fixture')
        self.write('data/status_decals.json',json.dumps(dict(effects=[dict(id='hydro')])).encode())
        self.write('generated/status-decals/hydro.spr',b'color decal')
        self.write('assets/audio/operator-deaths/manifest.json',json.dumps(dict(clips=[dict(path='vf_deaths/rocco/standard_v2.wav')])).encode())
        self.write('assets/audio/operator-deaths/rocco/standard_v2.wav',b'death sound')
        self.write('generated/death-sfx/manifest.json',json.dumps(dict(clips=[dict(path='vf_death_sfx/death_electro.wav'),dict(path='vf_death_sfx/dismemberment_standard.wav')])).encode())
        self.write('generated/death-sfx/sound/death_electro.wav',b'element death')
        self.write('generated/death-sfx/sound/dismemberment_standard.wav',b'detachment')
        self.write('generated/test-room/vf_range.bsp',b'target room')
        self.write('generated/weapon-fx/range/vf_fx_range.bsp',b'FX room')
        for source,target in release.deployment_files(self.root):
            out=self.dest/target;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,out)

    def write(self,path,data):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)

    def test_complete_delivery_is_verified(self):
        result=release.verify_deployment(self.dest,self.root);self.assertGreater(result['models'],10)

    def test_stale_third_person_carrier_is_detected(self):
        (self.dest/'models/vf_r01/r01_tp_top.mdl').write_bytes(b'old rig')
        with self.assertRaisesRegex(RuntimeError,'r01_tp_top'):release.verify_deployment(self.dest,self.root)

    def test_missing_source_carrier_cannot_hide_behind_empty_glob(self):
        (self.root/'generated/third-person/r01_tp.mdl').unlink()
        with self.assertRaisesRegex(FileNotFoundError,'r01_tp.mdl'):release.verify_deployment(self.dest,self.root)

    def test_missing_piece_named_in_manifest_is_detected(self):
        (self.root/'generated/r01/r01_receiver_a.mdl').unlink()
        with self.assertRaisesRegex(FileNotFoundError,'r01_receiver_a'):release.verify_deployment(self.dest,self.root)

    def test_missing_required_hud_decal_cannot_hide_behind_empty_glob(self):
        (self.root/'generated/status-decals/hydro.spr').unlink()
        with self.assertRaisesRegex(FileNotFoundError,'hydro.spr'):release.verify_deployment(self.dest,self.root)

    def test_stale_hud_decal_is_detected(self):
        (self.dest/'sprites/vf_status/hydro.spr').write_bytes(b'old decal')
        with self.assertRaisesRegex(RuntimeError,'hydro.spr'):release.verify_deployment(self.dest,self.root)

    def test_missing_death_sound_is_detected(self):
        (self.dest/'sound/vf_deaths/rocco/standard_v2.wav').unlink()
        with self.assertRaisesRegex(FileNotFoundError,'standard_v2.wav'):release.verify_deployment(self.dest,self.root)

    def test_stale_death_sound_is_detected(self):
        (self.dest/'sound/vf_deaths/rocco/standard_v2.wav').write_bytes(b'old death')
        with self.assertRaisesRegex(RuntimeError,'standard_v2.wav'):release.verify_deployment(self.dest,self.root)

    def test_missing_elemental_death_sfx_is_detected(self):
        (self.dest/'sound/vf_death_sfx/death_electro.wav').unlink()
        with self.assertRaisesRegex(FileNotFoundError,'death_electro.wav'):release.verify_deployment(self.dest,self.root)

    def test_stale_detachment_sfx_is_detected(self):
        (self.dest/'sound/vf_death_sfx/dismemberment_standard.wav').write_bytes(b'old detachment')
        with self.assertRaisesRegex(RuntimeError,'dismemberment_standard.wav'):release.verify_deployment(self.dest,self.root)

    def test_stale_server_dll_is_detected(self):
        (self.dest/'dlls/hl.dll').write_bytes(b'old server')
        with self.assertRaisesRegex(RuntimeError,'hl.dll'):release.verify_deployment(self.dest,self.root)

    def test_missing_room_is_detected(self):
        (self.dest/'maps/vf_range.bsp').unlink()
        with self.assertRaisesRegex(FileNotFoundError,'vf_range.bsp'):release.verify_deployment(self.dest,self.root)

    def test_stale_room_is_detected(self):
        (self.dest/'maps/vf_range.bsp').write_bytes(b'old room')
        with self.assertRaisesRegex(RuntimeError,'vf_range.bsp'):release.verify_deployment(self.dest,self.root)

    def test_missing_fx_room_is_detected(self):
        (self.root/'generated/weapon-fx/range/vf_fx_range.bsp').unlink()
        with self.assertRaisesRegex(FileNotFoundError,'vf_fx_range.bsp'):release.verify_deployment(self.dest,self.root)

    def test_wrong_renderer_interface_is_rejected_before_delivery(self):
        client=self.root/'build/client/client.dll';client.write_bytes(b'v3 connected')
        engine=Path(self.temp.name)/'engine';engine.mkdir();(engine/'vector-engine-build.json').write_text('{"extension_version":2}')
        with self.assertRaises(RuntimeError):release.check_native_interface(engine,client)
        self.assertEqual(b'fixture',(self.dest/'cl_dlls/client.dll').read_bytes())

    def test_canonical_startup_loads_voice_policy_once(self):
        self.assertEqual(1,release.startup().count('exec vf_voice_behavior.cfg'))
        self.assertNotIn('vf_commit',release.startup())


class BotDeliveryTests(unittest.TestCase):
    def test_bot_launcher_refreshes_models_and_maps_with_the_dlls(self):
        spec=importlib.util.spec_from_file_location('bot_delivery',ROOT/'bots/prepare_jk_botti.py')
        bots=importlib.util.module_from_spec(spec);spec.loader.exec_module(bots)
        with tempfile.TemporaryDirectory() as folder:
            project=Path(folder);vf=project/'vector-fields';engine=project/'engine';mod=engine/'valve'
            relatives=['dlls/hl.dll','cl_dlls/client.dll','models/vf_deaths/persona_death_gibs.mdl','maps/vf_range.bsp']
            files=[]
            for index,relative in enumerate(relatives):
                source=vf/'generated'/Path(relative).name;source.parent.mkdir(parents=True,exist_ok=True);source.write_bytes(('current '+str(index)).encode())
                target=mod/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'old release')
                files.append((source,Path(relative)))
            (mod/'vf').mkdir()
            (vf/'data').mkdir();(vf/'data/voice_behavior.cfg').write_text('voice fixture',encoding='ascii')
            bank=vf/'assets/audio/operators';bank.mkdir(parents=True);(bank/'manifest.json').write_text('{"clips":[]}',encoding='utf-8')
            with patch.object(bots,'PROJECT',project),patch.object(release,'deployment_files',return_value=files),patch.object(release,'verify_deployment') as verify,patch.object(release,'prepare_native_renderer_update') as update,patch.object(release,'check_native_interface') as interface,patch('death_voice_workshop.deploy'):
                bots.sync_voice_runtime(engine)
            for source,relative in files:self.assertEqual(source.read_bytes(),(mod/relative).read_bytes())
            verify.assert_called_once_with(mod,vf)
            update.assert_called_once_with(engine,vf/'build/client/client.dll')
            interface.assert_called_once_with(engine,vf/'build/client/client.dll')


    def test_bot_renderer_mismatch_is_rejected_before_asset_replacement(self):
        spec=importlib.util.spec_from_file_location('bot_delivery',ROOT/'bots/prepare_jk_botti.py')
        bots=importlib.util.module_from_spec(spec);spec.loader.exec_module(bots)
        with tempfile.TemporaryDirectory() as folder:
            project=Path(folder);vf=project/'vector-fields';engine=project/'engine';engine.mkdir()
            source=vf/'build/client/client.dll';source.parent.mkdir(parents=True);source.write_bytes(b'v3 connected')
            target=engine/'valve/cl_dlls/client.dll';target.parent.mkdir(parents=True);target.write_bytes(b'old client')
            with patch.object(bots,'PROJECT',project),patch.object(release,'deployment_files',return_value=[(source,Path('cl_dlls/client.dll'))]),patch.object(release,'prepare_native_renderer_update',return_value=False):
                with self.assertRaisesRegex(RuntimeError,'versions differ'):bots.sync_voice_runtime(engine)
            self.assertEqual(target.read_bytes(),b'old client')


if __name__=='__main__':unittest.main()

"""Real SMD round-trip and artist edits through camera-sector regeneration."""
import sys,tempfile,unittest
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from traversal_hands import extend
from build_traversal import pose
from third_person import smd
import traversal_editor as editor

class TraversalEditorTest(unittest.TestCase):
 def setUp(self):
  self.model=extend(Studio(ROOT/'generated/r01/r01_rig.mdl'))
  self.frames=np.array([pose(self.model,'vf_hang_idle',t)for t in (0,.5,1)])
  self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def write(self,frames=None):
  path=self.folder/'test.smd';smd(self.model,self.frames if frames is None else frames,path);return path
 def test_round_trip_keeps_full_rig_and_transforms(self):
  result=editor.read(self.write(),self.model)
  self.assertLess(np.max(np.abs(result-self.frames)),1e-6)
  self.assertEqual(len(self.model.names),62)
 def test_combined_scene_mesh_keeps_binding_at_every_frame(self):
  from build_traversal_body import triangle_lines
  # Real R1 finger vertices in the original mesh bind, with two independently
  # moved hanging frames. Simulate how SMD import binds its mesh to time zero.
  bone=16;points=[np.array([0.,0.,0.,1.]),np.array([.2,0.,0.,1.]),np.array([0.,.3,0.,1.])]
  mesh=[('test.bmp',[dict(b=bone,p=(self.model.bind[bone]@p)[:3],n=self.model.bind[bone][:3,2],uv=np.array([0.,0.]))for p in points])]
  triangles=triangle_lines(mesh,None);frames=self.frames.copy()
  frames[0,0,:3,3]+=[4.,-3.,8.]
  frames[1,16,:3,:3]=Rotation.from_euler('x',.43).as_matrix()@frames[1,16,:3,:3]
  scene=editor.posed_triangles(self.model,frames,triangles)
  undo=np.eye(4);undo[:3,:3]=Rotation.from_euler('z',-90,degrees=True).as_matrix()
  first=undo@editor.globals_of(frames[0],self.model.parents)[bone]
  for row,local in zip(scene[1:4],points):
   vertex=np.r_[np.array(row.split()[1:4],float),1.]
   self.assertLess(np.max(np.abs(np.linalg.inv(first)@vertex-local)),1e-7)
   for frame in frames:
    current=undo@editor.globals_of(frame,self.model.parents)[bone]
    imported=current@np.linalg.inv(first)@vertex
    self.assertLess(np.max(np.abs(imported-current@local)),1e-7)
 def test_hanging_thumbs_spread_away_from_middle_fingers(self):
  for frame in self.frames:
   g=editor.globals_of(frame,self.model.parents)
   for wrist,prefix,sign in [(12,'',1),(6,'VFRight_',-1)]:
    inv=np.linalg.inv(g[wrist]);base=(inv@g[self.model.names.index(prefix+'Bone43')])[:3,3];tip=(inv@g[self.model.names.index(prefix+'Bone45')])[:3,3]
    self.assertGreater(sign*(tip[0]-base[0]),2.)
 def test_changed_parent_is_rejected(self):
  p=self.write();p.write_text(p.read_text().replace('13 "Bone43" 12','13 "Bone43" 6'))
  with self.assertRaisesRegex(ValueError,'parent'):editor.read(p,self.model)
 def test_invalid_transform_is_rejected(self):
  p=self.write();p.write_text(p.read_text().replace('time 0\n0 ', 'time 0\n0 nan ',1))
  with self.assertRaises(ValueError):editor.read(p,self.model)
 def test_missing_bone_is_rejected(self):
  p=self.write();p.write_text(p.read_text().replace('43 "VFRight_Bone43" 6\n',''))
  with self.assertRaises(ValueError):editor.read(p,self.model)
 def test_hang_idle_finger_edit_reaches_camera_sectors(self):
  frames=self.frames.copy();frames[:,16,:3,:3]=Rotation.from_euler('x',.17).as_matrix()@frames[:,16,:3,:3]
  (self.folder/'first-person').mkdir();smd(self.model,frames,self.folder/'first-person/vf_hang_idle_0.smd')
  default=np.array([pose(self.model,'vf_hang_both_3',t,135,30)for t in (0,.5,1)])
  old=editor.EDITS
  try:
   editor.EDITS=self.folder;result=editor.override(self.model,default,'first-person','vf_hang_both_3',0,135,30)
  finally:editor.EDITS=old
  self.assertLess(np.max(np.abs(result[:,16,:3,:3]-frames[:,16,:3,:3])),1e-6)
  self.assertGreater(np.max(np.abs(result[:,16,:3,:3]-default[:,16,:3,:3])),.05)
 def test_stretched_arm_is_rejected(self):
  frames=self.frames.copy();frames[:,10,:3,3]*=1.4
  (self.folder/'first-person').mkdir();smd(self.model,frames,self.folder/'first-person/vf_hang_idle_0.smd')
  old=editor.EDITS
  try:
   editor.EDITS=self.folder
   with self.assertRaisesRegex(ValueError,'lengths'):editor.override(self.model,self.frames,'first-person','vf_hang_idle',0)
  finally:editor.EDITS=old
 def test_new_manual_vault_replaces_only_accepted_legacy_revision(self):
  default=np.array([pose(self.model,'vf_vault',t)for t in (0,.5,1)])
  edited=default.copy();edited[1,13,:3,:3]=Rotation.from_euler('x',.2).as_matrix()@edited[1,13,:3,:3]
  folder=self.folder/'first-person';folder.mkdir();path=folder/'vf_vault_0.smd';smd(self.model,edited,path)
  old=editor.EDITS
  try:
   editor.EDITS=self.folder
   np.testing.assert_allclose(editor.override(self.model,default,'first-person','vf_vault',0),default)
   path.with_suffix('.accepted.json').write_text('{"revision":"one-hand"}')
   accepted=editor.override(self.model,default,'first-person','vf_vault',0)
   self.assertGreater(np.max(np.abs(accepted[1,13]-default[1,13])),.05)
   np.testing.assert_allclose(accepted[:,10,:3,3],default[:,10,:3,3],atol=1e-6)
  finally:editor.EDITS=old
if __name__=='__main__':unittest.main()

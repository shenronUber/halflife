"""Validate compiled review poses against original R1 tracks and real meshes."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import sequence_frames,globals_of
from build_traversal import VARIANTS

def main():
    report={'preserved_sequences':0,'endpoint_samples':0,'max_endpoint_error':0.,'minimum_dorsal_alignment':1.,'aim_samples':0,'max_head_target_error':0.,'max_lower_body_error':0.,'max_spine_joint_turn':0.,'minimum_firing_arm_extension':1.,'maximum_wrist_height_error':0.,'minimum_arm_separation':999.,'first_person_aim_samples':0,'maximum_first_person_grip_error':0.}
    baseline=ROOT/'docs/validation/traversal/review-backups/generated'
    for name in VARIANTS:
        original=Studio(ROOT/'generated/r01'/(name+'.mdl'))
        reviewed=Studio(ROOT/'generated/traversal'/(name+'_tr.mdl'))
        indices=[reviewed.names.index(n)for n in original.names]
        for seq in original.sequences:
            assert np.max(np.abs(sequence_frames(original,seq)-sequence_frames(reviewed,seq)[:,indices]))<.01,(name,seq)
            report['preserved_sequences']+=1
        normal=sequence_frames(original,'idle')[0]
        equipped=globals_of(normal,original.parents)
        hand_to_gun=np.linalg.inv(equipped[original.names.index('Bone07')])@equipped[original.names.index('Bone76')]
        for sector in range(8):
            for corner,offset in enumerate((-22.5,22.5,-22.5,22.5)):
                from traversal_aim import aim_deploy
                yaw=(sector*45+offset+180)%360-180
                g=globals_of(sequence_frames(reviewed,f'vf_hang_aim_{sector}',blend=corner)[0],reviewed.parents)
                hand=reviewed.names.index('Bone07');gun=reviewed.names.index('Bone76')
                error=float(np.max(np.abs(np.linalg.inv(g[hand])@g[gun]-hand_to_gun)))
                report['maximum_first_person_grip_error']=max(report['maximum_first_person_grip_error'],error)
                assert error<.015,(name,sector,corner,'equipped gun grip must follow reviewed hand',error)
                if aim_deploy(yaw)==0:assert g[gun][2,1]>.999,(name,sector,corner,'view guard barrel must point up',g[gun][2,1])
                report['first_person_aim_samples']+=1
        arms=[original.names.index(n)for n in ('Bone05','Bone06','Bone07','Bone40','Bone41','Bone42')]
        for seq,frame in [('vf_hang_catch',0),('vf_vault',0),('vf_vault',-1),('vf_climb',-1),('vf_drop',-1),('vf_slide_end',-1)]:
            pose=sequence_frames(reviewed,seq)[frame][indices]
            error=float(np.max(np.abs(pose[arms]-normal[arms])))
            report['max_endpoint_error']=max(report['max_endpoint_error'],error)
            assert error<.012,(name,seq,frame,error)
            report['endpoint_samples']+=1
    from third_person import Author
    author=Author()
    for name,platform in [('r01_tp','bottom'),('r01_tp_side','side'),('r01_tp_top','top')]:
        original=Studio(baseline/'third-person'/(name+'.mdl'));reviewed=Studio(ROOT/'generated/third-person'/(name+'.mdl'))
        for seq in original.sequences[:81]:
            # Aim channels are authored as two independent tracks.
            from animation_assets import sequence_info
            for corner in range(sequence_info(original,seq)['blends']):
                assert np.max(np.abs(sequence_frames(original,seq,blend=corner)-sequence_frames(reviewed,seq,blend=corner)))<.01,(name,seq,corner)
            report['preserved_sequences']+=1
        normal=author.frame(author.neutral,platform)
        for seq,frame in [('vf_hang_catch',0),('vf_vault',0),('vf_vault',-1),('vf_climb',-1),('vf_drop',-1),('vf_slide_end',-1)]:
            error=float(np.max(np.abs(sequence_frames(reviewed,seq)[frame]-normal)))
            report['max_endpoint_error']=max(report['max_endpoint_error'],error)
            assert error<.012,(name,seq,error)
            report['endpoint_samples']+=1
        pose=sequence_frames(reviewed,'vf_hang_idle')[0];g=globals_of(pose,reviewed.parents)
        for n in ('Bip01 L Hand','Bip01 R Hand'):
            i=reviewed.names.index(n);dorsal=-g[i][:3,1]
            alignment=float(dorsal@np.array([-1.,0,0]));report['minimum_dorsal_alignment']=min(report['minimum_dorsal_alignment'],alignment)
            assert alignment>.93,(name,n,alignment)
        from scipy.spatial.transform import Rotation
        from traversal_aim import body_turn,head_turn,left_lean,left_route,left_cross_arm
        idle=sequence_frames(reviewed,'vf_hang_idle')[0];ig=globals_of(idle,reviewed.parents)
        previous=Studio(ROOT/'docs/validation/traversal/review-backups/guard-before-left/third-person'/(name+'.mdl'))
        from traversal_torso_clearance import TorsoGuard
        torso=TorsoGuard(ROOT/'generated/personas/persona_scout.mdl',reviewed.names)
        ng=globals_of(normal,reviewed.parents);face_axis=ng[13][:3,:3].T@np.array([1.,0,0])
        for sector in range(8):
            for corner,(offset,pitch) in enumerate([(-22.5,-70),(22.5,-70),(-22.5,70),(22.5,70)]):
                yaw=(sector*45+offset+180)%360-180
                pose=sequence_frames(reviewed,f'vf_hang_aim_{sector}',blend=corner)[0];g=globals_of(pose,reviewed.parents)
                weight=left_lean(yaw)
                planted=g[:8].copy();planted[:,2,3]+=22
                shift=planted[0,:3,3]-ig[0,:3,3]
                assert abs(shift[1])<.012 and abs(shift[2]-3*weight)<.012 and abs(shift[0])<6.012,(name,sector,corner,'bounded left lean root',shift)
                planted[:,:3,3]-=shift
                error=float(np.max(np.abs(planted-ig[:8])))
                report['max_lower_body_error']=max(report['max_lower_body_error'],error)
                assert error<.012,(name,sector,corner,'lower joints must retain hanging shape',error)
                assert np.max(np.abs(g[17][:3,3]+[0,0,22]-ig[17][:3,3]))<.012,(name,sector,corner,'left wrist must stay fixed')
                if weight==0 and left_route(yaw)==0:
                    prior=sequence_frames(previous,f'vf_hang_aim_{sector}',blend=corner)[0]
                    assert np.max(np.abs(pose-prior))<.012,(name,sector,corner,'right and guard poses must remain unchanged')
                else:
                    report['left_lean_samples']=report.get('left_lean_samples',0)+1
                    report['maximum_left_lift']=max(report.get('maximum_left_lift',0),float(shift[2]))
                support_reach=sum(np.linalg.norm(g[b][:3,3]-g[a][:3,3])for a,b in ((15,16),(16,17)))
                support_extension=np.linalg.norm(g[17][:3,3]-g[15][:3,3])/support_reach
                if weight>.7:assert support_extension>.9,(name,sector,corner,'left support arm must extend',support_extension)
                shoulder,elbow,wrist=(g[i][:3,3] for i in (22,23,24))
                a=np.linalg.norm(elbow-shoulder);b=np.linalg.norm(wrist-elbow);reach=a+b
                extension=float(np.linalg.norm(wrist-shoulder)/reach)
                from traversal_aim import aim_deploy
                deploy=aim_deploy(yaw)
                route=left_route(yaw)
                if deploy==1:
                    report['minimum_firing_arm_extension']=min(report['minimum_firing_arm_extension'],extension)
                    assert (.62 if route>.999 else .25)<extension<.95,(name,sector,corner,'anatomical firing reach',extension)
                    if route==0:assert .935<extension<.945,(name,sector,corner,'right firing extension preserved',extension)
                span=g[15][:3,3]-shoulder;chest=np.arctan2(-span[0],span[1])
                wanted,_,_=left_cross_arm(yaw,a,b,chest)
                prior_g=globals_of(sequence_frames(previous,f'vf_hang_aim_{sector}',blend=corner)[0],previous.parents)
                delta=(1-route)*(prior_g[24][:3,3]-prior_g[22][:3,3])+route*np.array(wanted)
                assert np.max(np.abs(wrist-shoulder-delta))<.025,(name,sector,corner,'routed firing wrist',wrist-shoulder,delta)
                rise=delta[2]
                height_error=abs(wrist[2]-shoulder[2]-rise)
                report['maximum_wrist_height_error']=max(report['maximum_wrist_height_error'],float(height_error))
                assert height_error<.015,(name,sector,corner,'wrist must clear the support shoulder only on left',height_error)
                if route>.999:
                    bend=float(np.degrees(np.arccos(np.clip((shoulder-elbow)@(wrist-elbow)/(a*b),-1,1))))
                    assert 75<bend<95,(name,sector,corner,'left crossing requires a bent elbow',bend)
                if route>.25:
                    clearance=torso.inspect(g,shoulder,elbow,wrist)
                    assert clearance[0]>-.08 and clearance[1]>1.5,(name,sector,corner,'firing arm must clear the torso',clearance)
                    report['torso_clearance_samples']=report.get('torso_clearance_samples',0)+1
                    report['minimum_forearm_torso_clearance']=min(report.get('minimum_forearm_torso_clearance',999),clearance[1])
                if deploy==0:assert g[28][2,1]>.999,(name,sector,corner,'guard barrel must point to ceiling',g[28][2,1])
                left=np.concatenate([np.linspace(g[a][:3,3],g[b][:3,3],101)for a,b in ((15,16),(16,17))])
                right=np.concatenate([np.linspace(g[a][:3,3],g[b][:3,3],101)for a,b in ((22,23),(23,24))])
                separation=float(np.linalg.norm(left[:,None,:]-right[None,:,:],axis=2).min())
                report['minimum_arm_separation']=min(report['minimum_arm_separation'],separation)
                assert separation>4.5,(name,sector,corner,'sleeves intersect',separation)
                hy,hp=head_turn(yaw,pitch)
                wanted=Rotation.from_euler('z',hy,degrees=True).as_matrix()@Rotation.from_euler('y',hp,degrees=True).as_matrix()@np.array([1.,0,0])
                face=g[13][:3,:3]@face_axis
                angle=float(np.degrees(np.arccos(np.clip(face@wanted,-1,1))))
                report['max_head_target_error']=max(report['max_head_target_error'],angle)
                assert angle<2,(name,sector,corner,'bounded head target',angle)
                for i in (8,9,10,11):
                    angle=float(np.degrees(Rotation.from_matrix(pose[i][:3,:3]@idle[i][:3,:3].T).magnitude()))
                    report['max_spine_joint_turn']=max(report['max_spine_joint_turn'],angle)
                    assert angle<14,(name,sector,corner,'lumbar turn and left lean',i,angle)
                report['aim_samples']+=1
        # A seated slide leads with the left heel; the right boot folds under
        # the seat and the right knee stays ahead of the pelvis.
        g=globals_of(sequence_frames(reviewed,'vf_slide_loop')[0],reviewed.parents)
        hip=g[1][:3,3];assert hip[2]<-8,(name,hip)
        assert g[4][0,3]-hip[0]>20,(name,'left heel must lead slide')
        assert g[6][0,3]-hip[0]>10 and abs(g[7][0,3]-hip[0])<4,(name,'right knee forwards and boot under seat')
        assert g[7][2,3]<hip[2] and abs(g[7][1,3]-g[5][1,3])<6,(name,'right foot stays below its hip')
        assert g[13][0,3]<8,(name,'torso must lean back')
        # The leading boot's toes face up. The tucked boot points back with
        # its sole down, rather than rotating sideways through the seat.
        assert g[4][2,1]>.97 and abs(g[4][1,1])<.02,(name,'left toes must point skywards')
        assert g[7][0,1]<-.99 and g[7][2,0]<-.99,(name,'tucked boot toe backwards and sole down')
    contacts=json.loads((ROOT/'animation-workshop/traversal/blender/verification/audit-traversal/after/corrections-third-person.json').read_text())['body_grip_contacts']
    assert all(abs(v['tip_gap'])<.12 and v['penetration']<.08 for v in contacts.values()),contacts
    report['body_grip_contacts']=contacts
    (ROOT/'docs/validation/traversal/review-assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PASS reviewed R1 animations',json.dumps(report))

if __name__=='__main__':main()

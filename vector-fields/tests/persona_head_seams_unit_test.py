"""Head joins change material without recoloring eyes, clothing or the hood."""
import sys,unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from persona_head_seams import normalize,pad_head_edges,JOINS
from studio_assets import smd_uv
import persona_head_continuity as continuity


class HeadJoinTests(unittest.TestCase):
    def setUp(self):
        self.masks={name:np.zeros((32,32),dtype=bool)for name in ('hood',*JOINS)}
        self.masks['hood'][15:25,15:25]=True
        self.masks['curved_join'][2:10,18:22]=True
        self.masks['rectangular_join'][2:7,10:14]=True
        self.masks['side_join'][2:10,25:29]=True
        self.layout=dict(masks=self.masks)
        self.image=np.full((32,32,3),[110,85,65],dtype='uint8')
        self.image[self.masks['hood']]=[12,45,140]
        for name in JOINS:self.image[self.masks[name]]=[175,20,25]

    def test_all_head_joins_match_blue_hood(self):
        corrected,report=normalize(Image.fromarray(self.image),self.layout)
        pixels=np.array(corrected)
        self.assertTrue(all(r['corrected']for r in report))
        for name in JOINS:
            np.testing.assert_array_equal(pixels[self.masks[name]],np.tile([12,45,140],(self.masks[name].sum(),1)))
        # Independent face, clothing and the hood remain byte-for-byte intact.
        np.testing.assert_array_equal(pixels[15:],self.image[15:])
        np.testing.assert_array_equal(pixels[:,:8],self.image[:,:8])

    def test_coherent_material_is_unchanged(self):
        self.image[self.masks['curved_join']]=[11,42,131]
        self.image[self.masks['rectangular_join']]=[13,50,147]
        self.image[self.masks['side_join']]=[12,45,140]
        corrected,report=normalize(Image.fromarray(self.image),self.layout)
        self.assertFalse(any(r['corrected']for r in report))
        np.testing.assert_array_equal(np.array(corrected),self.image)

    def test_authored_shirt_collar_survives_head_seam_correction(self):
        self.image[self.masks['curved_join']]=[215,145,175]
        corrected,report=normalize(Image.fromarray(self.image),self.layout,shirt_collar=True)
        pixels=np.array(corrected)
        np.testing.assert_array_equal(pixels[self.masks['curved_join']],self.image[self.masks['curved_join']])
        collar=next(r for r in report if r['island']=='curved_join')
        self.assertEqual(collar['material'],'shirt_collar')
        self.assertFalse(collar['corrected'])
        self.assertEqual(collar['pixels_changed'],0)
        for name in ('rectangular_join','side_join'):
            np.testing.assert_array_equal(pixels[self.masks[name]],np.tile([12,45,140],(self.masks[name].sum(),1)))

    def test_correction_is_idempotent_and_retains_shading(self):
        self.image[2:5,18:22]=[100,12,15]
        corrected,_=normalize(Image.fromarray(self.image),self.layout)
        again,report=normalize(corrected,self.layout)
        np.testing.assert_array_equal(np.array(again),np.array(corrected))
        self.assertFalse(any(r['corrected']for r in report))
        self.assertLess(np.array(corrected)[3,20].sum(),np.array(corrected)[8,20].sum())

    def test_uniform_black_join_can_match_light_hood(self):
        self.image[self.masks['hood']]=[185,182,179]
        for name in JOINS:self.image[self.masks[name]]=0
        corrected,_=normalize(Image.fromarray(self.image),self.layout)
        for name in JOINS:
            np.testing.assert_array_equal(np.array(corrected)[self.masks[name]],np.tile([185,182,179],(self.masks[name].sum(),1)))

    def test_mdl_texels_survive_the_compiler_coordinate_conversion(self):
        # Actual atlas points at the front/side join and the crown. Test the
        # external compiler convention, including finite decimal SMD output.
        for x,y in [(432,246),(507,322),(1,2),(0,510),(306,29)]:
            u,v=smd_uv([x/512,1-y/512],512,512)
            u,v=float(f'{u:.6f}'),float(f'{v:.6f}')
            self.assertEqual(int(u*511),x)
            self.assertEqual(511-int(v*511),y)

    def test_uv_gutter_extends_fabric_without_touching_eyes_or_shirt(self):
        rim=np.zeros((32,32),dtype=bool);rim[13:15,15:25]=True
        yy,xx=np.indices((32,32));yy[rim]=15
        layout=dict(padding=[dict(rim=rim,nearest=np.array([yy,xx]))])
        corrected,report=pad_head_edges(Image.fromarray(self.image),layout)
        pixels=np.array(corrected)
        np.testing.assert_array_equal(pixels[13:15,15:25],np.tile([12,45,140],(2,10,1)))
        np.testing.assert_array_equal(pixels[~rim],self.image[~rim])
        self.assertEqual(report['pixels_changed'],20)


class SurfaceContinuityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json
        from studio_assets import Studio
        from build_personas import donor
        root=Path(__file__).resolve().parents[1]
        config=json.loads((root/'assets/personas/personas.json').read_text())
        cls.layout=continuity.layout(Studio(donor(config)['path']).mesh())
        cls.source=np.array(Image.open(root/'assets/personas/reference-uv.png').convert('RGB'))

    def test_discontinuous_surfaces_share_colour_and_shading_after_filtering(self):
        image=np.full((512,512,3),[30,45,55],dtype='uint8')
        # A bright front next to a dark rear, across the donor's real UV cuts.
        image[:,410:]=[145,170,195]
        corrected,report=continuity.align(Image.fromarray(image),self.layout)
        self.assertEqual(report['head_charts'],4)
        self.assertEqual(report['seam_edges'],20)
        self.assertGreater(report['before']['mean_rgb'],15)
        self.assertLess(report['after']['mean_rgb'],.4)
        self.assertLess(report['after']['p95_rgb'],1)
        np.testing.assert_array_equal(np.array(corrected)[~self.layout['active']],image[~self.layout['active']])

    def test_generated_clothing_face_and_shirt_collar_pixels_are_discarded(self):
        layer=Image.new('RGB',(512,512),(245,0,250))
        selected,report=continuity.apply_head_layer(Image.fromarray(self.source),layer,self.layout)
        result=np.array(selected);mask=self.layout['retouch_mask']
        np.testing.assert_array_equal(result[~mask],self.source[~mask])
        np.testing.assert_array_equal(result[300:385,435:495],self.source[300:385,435:495])
        np.testing.assert_array_equal(result[230:267,305:395],self.source[230:267,305:395])
        self.assertTrue(report['face_preserved_exactly'])
        self.assertTrue(report['clothing_preserved_exactly'])

    def test_face_interior_and_adjacent_boots_survive_surface_fit(self):
        corrected,_=continuity.align(Image.fromarray(self.source),self.layout)
        result=np.array(corrected)
        # Eyes/nose at the centre of the front chart, and a boot UV island
        # packed alongside the narrow head strip, must retain their bytes.
        np.testing.assert_array_equal(result[305:365,445:480],self.source[305:365,445:480])
        np.testing.assert_array_equal(result[430:470,460:490],self.source[430:470,460:490])

    def test_palette_refit_keeps_clothing_indices_and_original_palette(self):
        source=Image.fromarray(self.source).quantize(64)
        corrected,report=continuity.fit_indexed_edges(source,self.layout)
        self.assertEqual(source.getpalette(),corrected.getpalette())
        np.testing.assert_array_equal(np.array(source)[~self.layout['active']],np.array(corrected)[~self.layout['active']])
        before,after=report['before']['colour'],report['after']['colour']
        self.assertLessEqual(after['mean_rgb']+.03*after['p95_rgb'],before['mean_rgb']+.03*before['p95_rgb'])


if __name__=='__main__':unittest.main()

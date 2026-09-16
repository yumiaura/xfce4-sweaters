from pathlib import Path
import tempfile
import unittest
from PIL import Image
from xfce4_sweaters import config
from xfce4_sweaters.textures import Registry, border

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.registry=Registry()
        self.cfg=config.validate({},self.registry.ids)

    def test_all_imported_patterns_are_rectangular_and_renderable(self):
        self.assertEqual(len(self.registry.ids),47)
        for name,spec in self.registry.specs.items():
            with self.subTest(pattern=name):
                self.assertTrue(all(len(r)==len(spec['rows'][0]) for r in spec['rows']))
                self.assertTrue(all(c=='.' or 0 <= ord(c)-97 < len(spec['colors']) for r in spec['rows'] for c in r))
                tile=self.registry.tile(name,'#7297b8',5)
                self.assertGreater(tile.width,0)

    def test_random_is_stable_and_shuffle_changes_distribution(self):
        original=[self.registry.resolve(self.cfg,str(x),0) for x in range(100)]
        self.assertEqual(original,[self.registry.resolve(self.cfg,str(x),0) for x in range(100)])
        self.assertGreater(len({v['texture'] for v in original}),20)
        shuffled=[self.registry.resolve(self.cfg,str(x),1) for x in range(100)]
        self.assertGreater(sum(a!=b for a,b in zip(original,shuffled)),80)

    def test_explicit_texture_and_color_survive_shuffle(self):
        style={**self.cfg,'texture':'zigzag','color':'#123456'}
        self.assertEqual(self.registry.resolve(style,'42',0),self.registry.resolve(style,'42',123))

    def test_first_matching_rule_and_title_filter(self):
        self.cfg['rules']=[{'wm_class':'firefox','title':'*Work*','texture':'twinkle'}, {'wm_class':'Fire*','texture':'checker'}]
        self.assertEqual(config.style_for(self.cfg,'Firefox','WORK tab')['texture'],'twinkle')
        self.assertEqual(config.style_for(self.cfg,'Firefox','Other')['texture'],'checker')
        self.assertEqual(config.style_for(self.cfg,'Terminal','WORK')['texture'],'random')

    def test_validation_rejects_invalid_inputs(self):
        cases=[{'width':True},{'width':100},{'stitch':0},{'enabled':1},{'color':'red'}, {'texture':'missing'},
               {'texture':[]},{'seed':-1},{'inactive_opacity':float('nan')},{'rules':[{}]}, {'rules':[{'wm_class':4}]}, {'unknown':1}]
        for case in cases:
            with self.subTest(case=case),self.assertRaises(ValueError):
                config.validate(case,self.registry.ids)

    def test_atomic_save_preserves_previous_valid_file_on_bad_update(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'config.json'
            config.save(path,self.cfg,self.registry.ids)
            before=path.read_bytes()
            with self.assertRaises(ValueError): config.save(path,{'width':-1},self.registry.ids)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(config.load(path,self.registry.ids),self.cfg)
            self.assertEqual(list(Path(temp).glob('.config-*')),[])

    def test_defaults_are_not_shared_mutable_state(self):
        self.cfg['rules'].append({'wm_class':'*','texture':'off'})
        self.assertEqual(config.validate({},self.registry.ids)['rules'],[])

    def test_ring_is_transparent_inside_and_filled_on_all_sides(self):
        style={**self.cfg,'texture':'zigzag','color':'#648e7b'}
        image=border(self.registry,300,180,style)
        self.assertIsNone(image.crop((24,24,276,156)).getchannel('A').getbbox())
        for pos in [(150,10),(150,170),(10,90),(290,90),(12,12),(287,167)]:
            self.assertEqual(image.getpixel(pos)[3],255)
        # Outer corners are rounded with radius width//2, so the very corner pixels are clear.
        for pos in [(0,0),(299,0),(0,179),(299,179)]:
            self.assertEqual(image.getpixel(pos)[3],0)

    def test_custom_png_validated_and_transparency_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            image=Image.new('RGBA',(4,4),(255,0,0,128)); image.save(directory/'sample.png')
            (directory/'broken.png').write_text('not an image')
            Image.new('RGB',(1025,1)).save(directory/'huge.png')
            registry=Registry(directory)
            self.assertIn('user:sample',registry.ids)
            self.assertEqual(len(registry.errors),2)
            style={'texture':'user:sample','color':'#123456','width':8,'stitch':4}
            output=border(registry,80,50,style)
            self.assertEqual(output.getpixel((40,2))[3],128)

    def test_inactive_alpha_and_dimension_limits(self):
        style={**self.cfg,'texture':'ribbon','color':'#8279ab'}
        image=border(self.registry,200,120,style,0.5)
        self.assertEqual(image.getpixel((100,5))[3],128)
        for w,h in [(20,20),(20000,200)]:
            with self.assertRaises(ValueError): border(self.registry,w,h,style)

if __name__=='__main__':
    unittest.main()

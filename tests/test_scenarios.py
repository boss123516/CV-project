import unittest
from cv_project.config import ROOT,read_json,scenario_config,pipeline_config
from cv_project.cli import main


class ScenarioTests(unittest.TestCase):
    def test_every_registered_scenario_has_an_executable_route_and_world(self):
        manifests=list((ROOT/'scenarios').glob('*/scenario.json'))
        self.assertGreaterEqual(len(manifests),6)
        for manifest in manifests:
            scene=scenario_config(manifest.parent.name)
            self.assertTrue((ROOT/scene['manifest']['world']).is_file())
            self.assertLess(scene['route_start_m'],scene['route_end_m'])

    def test_both_pipeline_profiles_use_the_same_depth_contract(self):
        for name in ['baseline','yolo26']:
            config=pipeline_config(f'config/pipelines/{name}.json')
            self.assertEqual(config['depth']['backend'],'sgbm')
            self.assertGreaterEqual(config['depth']['frame_cache_size'],64)

    def test_scenario_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):scenario_config('../urban_baseline')

    def test_cli_dry_run_does_not_require_ros_or_weights(self):
        self.assertEqual(main(['start','--pipeline','yolo26','--scenario','occluded_sign','--dry-run']),0)

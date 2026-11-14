import math
import unittest
from cv_project.config import scenario_config
from cv_project.simulation.mission import MissionDriver,wrap_angle

MISSIONS=['residential_detour','courtyard_detour','station_access_detour']


class MissionTests(unittest.TestCase):
    def test_each_mission_contacts_retreats_detours_and_reaches_its_destination(self):
        for identifier in MISSIONS:
            with self.subTest(mission=identifier):
                scene=scenario_config(identifier)
                config=dict(scene['mission'],repeat_after_s=None)
                mission=MissionDriver(config)
                phases=set();retreated=0.;headings=[]
                for _ in range(14000):
                    sample=mission.step(.032)
                    phases.add(sample.phase);headings.append(sample.heading)
                    retreated+=min(0.,sample.signed_distance)
                    # Human body clears the obstruction; the staged contact is with the cane.
                    for obstacle in config['obstacles']:
                        ox,oy=obstacle['center'];hx,hy=obstacle['half_extents']
                        dx=max(abs(sample.x-ox)-hx,0.);dy=max(abs(sample.y-oy)-hy,0.)
                        self.assertGreater(math.hypot(dx,dy),.24,identifier)
                    if sample.arrived:break
                self.assertTrue(mission.arrived,identifier)
                self.assertLess(mission.distance_to_goal,.04)
                self.assertEqual(mission.contact_count,1)
                self.assertLess(retreated,-.5)
                self.assertTrue({'contact','backtrack','scan','detour','arrive'}<=phases)
                self.assertGreater(max(headings)-min(headings),1.)
                self.assertTrue(all(abs(wrap_angle(b-a))<=mission.max_yaw_rate*.032+.001 for a,b in zip(headings,headings[1:])))
                self.assertEqual(mission.events[0]['type'],'staged_cane_contact')
                self.assertTrue(all(e['source']=='scenario_script' for e in mission.events))

    def test_pause_freezes_mission_progress_and_contact_timer(self):
        mission=MissionDriver(scenario_config('residential_detour')['mission'])
        for _ in range(200):mission.step(.032)
        point=(mission.x,mission.y,mission.index,mission.elapsed)
        for _ in range(100):mission.step(.032,paused=True)
        self.assertEqual(point,(mission.x,mission.y,mission.index,mission.elapsed))

    def test_repeat_and_explicit_reset_reinitialize_the_destination_mission(self):
        config=scenario_config('courtyard_detour')['mission']
        mission=MissionDriver(config)
        mission.x=8;mission.y=5.8;mission.index=len(mission.actions)-1
        mission.step(7.)
        self.assertEqual(mission.lap,1)
        self.assertEqual([mission.x,mission.y],config['start'])
        self.assertEqual(mission.contact_count,0)

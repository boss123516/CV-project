import unittest
from cv_project.config import scenario_config
from cv_project.simulation.mission import MissionDriver


class TrafficTests(unittest.TestCase):
    def test_red_wait_moving_cars_green_clear_and_destination(self):
        config=dict(scenario_config('signalized_crossing')['mission'],repeat_after_s=None)
        driver=MissionDriver(config)
        waits=[];crossed=[];maximum_speed=0.;seen=[]
        for _ in range(8000):
            sample=driver.step(.032)
            traffic=driver.traffic
            maximum_speed=max(maximum_speed,max(c['speed_mps'] for c in traffic.cars))
            if sample.phase=='signal_wait':waits.append((sample.x,sample.y,traffic.pedestrian_signal))
            if abs(sample.y)<3.6:
                self.assertEqual(traffic.pedestrian_signal,'green')
                self.assertTrue(traffic.crosswalk_clear)
                crossed.append(sample.y)
            seen.extend(event['type'] for event in driver.events[len(seen):])
            if sample.arrived:break
        self.assertTrue(driver.arrived)
        self.assertGreater(maximum_speed,5.)
        self.assertGreater(len(waits),100)
        self.assertTrue(any(v[2]=='red' for v in waits))
        self.assertTrue(all(abs(v[0])<.03 and abs(v[1]+4.5)<.03 for v in waits))
        self.assertGreater(len(crossed),100)
        self.assertIn('pedestrian_red_wait',seen)
        self.assertIn('pedestrian_green_clear',seen)

    def test_pausing_freezes_the_signal_and_vehicles(self):
        driver=MissionDriver(scenario_config('signalized_crossing')['mission'])
        driver.step(1.)
        before=driver.traffic.snapshot()
        for _ in range(30):driver.step(.032,paused=True)
        self.assertEqual(before,driver.traffic.snapshot())

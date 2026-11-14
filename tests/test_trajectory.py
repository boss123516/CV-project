import math
import unittest
from cv_project.simulation.trajectory import WalkingTrajectory
from cv_project.simulation.mission import wrap_angle


class CurvedWalkingTests(unittest.TestCase):
    def test_corner_tangents_are_continuous_and_not_axis_snaps(self):
        trajectory=WalkingTrajectory((0,0),0,[((3,0),0),((3,3),0),((6,3),0)])
        for corner in [(3,0),(3,3)]:
            index=min(range(len(trajectory.points)),key=lambda i:math.dist(trajectory.points[i],corner))
            distance=trajectory.arc[index]
            before=trajectory.heading(distance-.015);after=trajectory.heading(distance+.015)
            self.assertLess(abs(wrap_angle(after-before)),.16)
            self.assertGreater(abs(math.sin(trajectory.heading(distance))),.2)
            self.assertGreater(abs(math.cos(trajectory.heading(distance))),.2)

    def test_rendered_map_can_be_serialized_and_contains_curved_path_points(self):
        import json
        from cv_project.config import scenario_config
        from cv_project.simulation.mission import MissionDriver
        driver=MissionDriver(scenario_config('residential_detour')['mission'])
        data=driver.map_data()
        self.assertGreater(sum(len(leg['points']) for leg in data['legs']),100)
        json.dumps(data)

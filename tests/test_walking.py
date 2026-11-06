import unittest
import numpy as np
from webots.controllers.assistive_walker.walking_motion import foot_target,leg_ik,forward_ankle,STRIDE_M

class WalkingTests(unittest.TestCase):
    def test_stance_foot_stays_planted_in_world(self):
        positions=[]
        for phase in np.linspace(.01,.60,50):
            x,lift,pitch=foot_target(phase)
            positions.append(phase*STRIDE_M+x)
            self.assertEqual(lift,0.)
        self.assertLess(np.ptp(positions),1e-9)

    def test_leg_ik_reaches_ankle_targets(self):
        for phase in np.linspace(0,1,80):
            x,lift,pitch=foot_target(phase)
            z=.108-1.215+lift
            hip,knee,ankle=leg_ik(x,z,pitch)
            actual=forward_ankle(hip,knee)
            self.assertAlmostEqual(actual[0],x,places=7)
            self.assertAlmostEqual(actual[1],z,places=7)
            self.assertAlmostEqual(hip+knee+ankle,pitch,places=7)

if __name__=='__main__':unittest.main()

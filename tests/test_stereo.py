"""Known image shifts verify actual vision, metric reconstruction and rejection."""
import unittest
import cv2
import numpy as np
from perception.stereo import CameraModel,StereoEstimator,clock_direction,optical_to_person_transform


def cameras(cx_right=320.):
    k=np.array([[400.,0,320],[0,400.,160],[0,0,1.]])
    pl=np.column_stack([k,np.zeros(3)]);pr=pl.copy();pr[0,3]=-48.;pr[0,2]=cx_right
    kr=k.copy();kr[0,2]=cx_right
    return CameraModel(640,320,k,np.zeros(5),np.eye(3),pl),CameraModel(640,320,kr,np.zeros(5),np.eye(3),pr)


def pair(shift):
    rng=np.random.default_rng(42)
    left=cv2.GaussianBlur(rng.integers(0,256,(320,640,3),dtype=np.uint8),(3,3),0)
    right=np.zeros_like(left);right[:,:-shift]=left[:,shift:]
    return left,right


class StereoTests(unittest.TestCase):
    def test_known_shifts_reconstruct_three_and_six_meters(self):
        for shift,expected in [(16,3.),(8,6.)]:
            estimator=StereoEstimator(*cameras(),optical_to_person_transform([0,0,0],0),num_disparities=96)
            frame=estimator.compute(*pair(shift))
            result=estimator.localize(frame,{'id':1,'class':'test','bbox_xyxy':[220,100,400,250]})
            self.assertTrue(result['valid'],result)
            self.assertAlmostEqual(result['depth_m'],expected,delta=.08)
            self.assertGreater(result['inlier_pixels'],500)

    def test_camera_principal_point_difference_is_removed(self):
        estimator=StereoEstimator(*cameras(cx_right=315),optical_to_person_transform([0,0,0],0),num_disparities=96)
        result=estimator.localize(estimator.compute(*pair(16)),{'id':1,'class':'test','bbox_xyxy':[220,100,400,250]})
        self.assertTrue(result['valid'],result)
        self.assertAlmostEqual(result['depth_m'],48/11,delta=.08)

    def test_person_extrinsic_and_left_right_clock_directions(self):
        transform=optical_to_person_transform([.235,.06,1.67],.12)
        person=transform@np.array([.5,0.,3.,1.])
        self.assertLess(person[1],0)
        self.assertAlmostEqual(person[0],.235+3*np.cos(.12))
        self.assertAlmostEqual(person[2],1.67-3*np.sin(.12))
        for bearing,hour in [(0,12),(-30,11),(30,1),(-60,10),(60,2)]:
            actual_bearing,actual_hour=clock_direction(3.,-3*np.tan(np.radians(bearing)))
            self.assertAlmostEqual(actual_bearing,bearing)
            self.assertEqual(actual_hour,hour)

    def test_untextured_images_are_rejected_without_fallback(self):
        estimator=StereoEstimator(*cameras(),optical_to_person_transform([0,0,0],0),num_disparities=96)
        blank=np.full((320,640,3),128,np.uint8)
        result=estimator.localize(estimator.compute(blank,blank),{'id':1,'class':'test','bbox_xyxy':[220,100,400,250]})
        self.assertFalse(result['valid'])
        self.assertNotIn('distance_m',result)
        self.assertNotIn('person_xyz_m',result)

    def test_reversed_or_zero_baseline_is_rejected(self):
        left,right=cameras()
        for tx in [0.,48.]:
            right.p[0,3]=tx
            with self.assertRaises(ValueError):StereoEstimator(left,right,np.eye(4))

    def test_off_image_detection_is_rejected(self):
        estimator=StereoEstimator(*cameras(),optical_to_person_transform([0,0,0],0),num_disparities=96)
        result=estimator.localize(estimator.compute(*pair(16)),{'id':1,'class':'test','bbox_xyxy':[-100,5,-50,40]})
        self.assertFalse(result['valid'])


if __name__=='__main__':unittest.main()

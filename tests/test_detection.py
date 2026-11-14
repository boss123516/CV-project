import unittest
import numpy as np
from cv_project.detection.yolo26 import YOLO26Detector


class ArrayResult:
    def __init__(self,values):self.values=values
    def cpu(self):return self
    def tolist(self):return self.values


class ModelStub:
    def predict(self,**kwargs):
        self.options=kwargs
        boxes=type('Boxes',(),{'xyxy':ArrayResult([[10,20,100,200]]),
            'conf':ArrayResult([.87]),'cls':ArrayResult([0])})()
        return [type('Result',(),{'boxes':boxes,'names':{0:'person'}})()]


class DetectorTests(unittest.TestCase):
    def test_adapter_maps_model_output_without_simulator_information(self):
        model=ModelStub()
        detector=YOLO26Detector('unused',class_map={'person':'pedestrian'},model=model)
        image=np.zeros((240,320,3),np.uint8)
        detection=detector.detect(image)[0].as_dict()
        self.assertEqual(detection['class'],'pedestrian')
        self.assertIsNone(detection['id'])
        self.assertAlmostEqual(detection['confidence'],.87)
        self.assertEqual(detection['bbox_xyxy'],[10,20,100,200])
        self.assertIs(model.options['source'],image)

    def test_missing_weights_do_not_fall_back_to_simulator(self):
        with self.assertRaises(FileNotFoundError):YOLO26Detector('/definitely/missing/yolo26.pt')


class ScopeFilterTests(unittest.TestCase):
    def test_scope_filter_drops_unrequested_classes_without_relabeling_them(self):
        model=ModelStub()
        detector=YOLO26Detector('unused',model=model,class_allowlist=['car'])
        self.assertEqual(detector.detect(np.zeros((240,320,3),np.uint8)),[])

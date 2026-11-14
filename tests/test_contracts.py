import unittest
from cv_project.contracts import Detection,detection_packet,validate_detection_packet
from cv_project.detection.simulator import convert_simulator_packet


class ContractTests(unittest.TestCase):
    def test_simulator_geometry_cannot_cross_detector_boundary(self):
        data={'simulation_time':1.024,'objects':[{'id':7,'class':'bench','center_px':[320,240],
              'size_px':[60,80],'range_m':999,'camera_position_m':[123,456,789]}]}
        packet=convert_simulator_packet(data)
        self.assertEqual(packet['stamp_ns'],1024000000)
        self.assertEqual(packet['detections'][0]['bbox_xyxy'],[290,200,350,280])
        self.assertEqual(set(packet['detections'][0]),{'id','class','bbox_xyxy','confidence'})

    def test_raw_coordinates_and_bad_timestamps_are_rejected(self):
        packet=detection_packet(64,[Detection('bench',(0,0,20,20))],'test')
        packet['coordinate_space']='raw_left'
        with self.assertRaises(ValueError):validate_detection_packet(packet)
        for stamp in [-1,1.5,True]:
            with self.assertRaises(ValueError):detection_packet(stamp,[],'test')

    def test_nonfinite_boxes_are_rejected(self):
        for box in [(0,0,float('nan'),1),(2,0,1,10),(0,0,2,float('inf'))]:
            with self.assertRaises(ValueError):Detection('test',box).as_dict()

    def test_incoming_extra_fields_are_not_forwarded(self):
        packet=detection_packet(64,[Detection('bench',(0,0,20,20))],'test')
        packet['detections'][0]['camera_position_m']=[1,2,3]
        cleaned=validate_detection_packet(packet)
        self.assertNotIn('camera_position_m',cleaned['detections'][0])

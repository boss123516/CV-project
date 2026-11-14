"""Rectified stereo -> robust object surface position -> person-relative direction.

No simulator positions or object dimensions are accepted by this module.
All distance measurements come from left/right image correspondence.
"""
from dataclasses import dataclass
import math
import time
import cv2
import numpy as np


@dataclass
class CameraModel:
    width: int
    height: int
    k: np.ndarray
    d: np.ndarray
    r: np.ndarray
    p: np.ndarray

    @classmethod
    def from_ros(cls, message):
        if message.distortion_model not in ['', 'plumb_bob', 'rational_polynomial']:
            raise ValueError('Unsupported distortion model: '+message.distortion_model)
        return cls(message.width,message.height,np.asarray(message.k,float).reshape(3,3),
                   np.asarray(message.d,float),np.asarray(message.r,float).reshape(3,3),
                   np.asarray(message.p,float).reshape(3,4))


@dataclass
class StereoFrame:
    disparity_px: np.ndarray
    valid_mask: np.ndarray
    rectified_left: np.ndarray
    processing_ms: float


def optical_to_person_transform(translation_m,downward_pitch_rad):
    """Extrinsic calibration: optical (right,down,forward) -> person (forward,left,up)."""
    c=math.cos(downward_pitch_rad); s=math.sin(downward_pitch_rad)
    transform=np.eye(4)
    transform[:3,:3]=[[0,-s,c],[-1,0,0],[0,-c,-s]]
    transform[:3,3]=translation_m
    return transform


def clock_direction(forward_m,left_m):
    """Clockwise azimuth; forward=12, left=11/10, right=1/2."""
    bearing=math.degrees(math.atan2(-left_m,forward_m))
    hour=int(math.floor(bearing/30+0.5))%12 or 12
    return bearing,hour


class StereoEstimator:
    def __init__(self,left,right,person_from_optical,*,num_disparities=128,block_size=5,
                 min_distance_m=.6,max_distance_m=10.,lr_tolerance_px=1.5,min_inlier_pixels=24):
        if (left.width,left.height)!=(right.width,right.height):
            raise ValueError('Stereo image dimensions differ')
        if num_disparities<=0 or num_disparities%16:
            raise ValueError('num_disparities must be a positive multiple of 16')
        if block_size<3 or block_size%2==0:
            raise ValueError('block_size must be an odd number >=3')
        self.left=left;self.right=right
        self.fx=float(left.p[0,0]);self.fy=float(left.p[1,1])
        self.cx=float(left.p[0,2]);self.cy=float(left.p[1,2])
        if self.fx<=0 or self.fy<=0 or float(right.p[0,0])<=0:
            raise ValueError('Invalid focal length')
        if (not np.isclose(self.fx,right.p[0,0],rtol=1e-4)
                or not np.isclose(self.fy,right.p[1,1],rtol=1e-4)
                or not np.isclose(self.cy,right.p[1,2],atol=.05)
                or abs(left.p[1,3])+abs(right.p[1,3])>1e-6):
            raise ValueError('P matrices must describe a common horizontal rectified stereo pair')
        self.baseline=float(left.p[0,3]/self.fx-right.p[0,3]/right.p[0,0])
        if self.baseline<=1e-5:
            raise ValueError('Right camera must be to the right of the left camera; baseline must be positive')
        self.cx_difference=float(left.p[0,2]-right.p[0,2])
        self.person_from_optical=np.asarray(person_from_optical,float)
        if self.person_from_optical.shape!=(4,4): raise ValueError('Extrinsic must be a 4x4 matrix')
        rotation=self.person_from_optical[:3,:3]
        if not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-5) or not np.isclose(np.linalg.det(rotation),1.):
            raise ValueError('Extrinsic rotation must be a proper orthonormal matrix')
        self.min_distance=float(min_distance_m);self.max_distance=float(max_distance_m)
        if not 0<self.min_distance<self.max_distance: raise ValueError('Invalid distance limits')
        self.lr_tolerance=float(lr_tolerance_px);self.min_pixels=int(min_inlier_pixels)
        self.num_disparities=num_disparities
        self.maps=[self._rectification_maps(c) for c in [left,right]]
        options=dict(minDisparity=0,numDisparities=num_disparities,blockSize=block_size,
                     P1=8*block_size**2,P2=32*block_size**2,disp12MaxDiff=1,
                     uniquenessRatio=8,speckleWindowSize=60,speckleRange=2,preFilterCap=31,
                     mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
        self.matcher=cv2.StereoSGBM_create(**options)

    @staticmethod
    def _rectification_maps(camera):
        if np.allclose(camera.d,0) and np.allclose(camera.r,np.eye(3)) and np.allclose(camera.k,camera.p[:3,:3]):
            return None
        return cv2.initUndistortRectifyMap(camera.k,camera.d,camera.r,camera.p[:3,:3],
                                         (camera.width,camera.height),cv2.CV_32FC1)

    def compute(self,left_image,right_image):
        start=time.perf_counter(); gray=[];rectified=[]
        for image,maps in zip([left_image,right_image],self.maps):
            if image.shape[:2]!=(self.left.height,self.left.width): raise ValueError('Image and calibration sizes differ')
            image=cv2.remap(image,*maps,cv2.INTER_LINEAR) if maps is not None else image
            rectified.append(image)
            gray.append(image if image.ndim==2 else cv2.cvtColor(image,cv2.COLOR_BGR2GRAY))
        disparity=self.matcher.compute(gray[0],gray[1]).astype(np.float32)/16.
        # Match a flipped pair to obtain positive disparities in the right image.
        right_disparity=np.fliplr(self.matcher.compute(np.ascontiguousarray(np.fliplr(gray[1])),
                                                      np.ascontiguousarray(np.fliplr(gray[0])))).astype(np.float32)/16.
        h,w=disparity.shape; columns=np.arange(w)[None,:]
        right_columns=np.rint(columns-disparity).astype(np.int32)
        in_bounds=(right_columns>=0)&(right_columns<w)
        right_values=right_disparity[np.arange(h)[:,None],np.clip(right_columns,0,w-1)]
        corrected=disparity-self.cx_difference
        fb=self.fx*self.baseline
        valid=(in_bounds & (disparity>0) & (right_values>0)
               & (np.abs(disparity-right_values)<=self.lr_tolerance)
               & (corrected>=fb/self.max_distance) & (corrected<=fb/self.min_distance))
        return StereoFrame(disparity,valid,rectified[0],(time.perf_counter()-start)*1000)

    def localize(self,frame,detection):
        """Estimate a representative visible surface patch inside a rectified bbox.

        detection = {id, class, bbox_xyxy}; bbox coordinates must refer to the
        rectified left image, as with a detector run on rectified frames.
        """
        result={'id':detection.get('id'),'class':detection['class'],'valid':False,
                'source':'stereo_sgbm','bbox_xyxy':list(detection['bbox_xyxy'])}
        x1,y1,x2,y2=map(float,detection['bbox_xyxy']);w=x2-x1;h=y2-y1
        if w<3 or h<3: return dict(result,reason='bbox_too_small')
        # Remove bbox borders and lower ground pixels; retain the central surface.
        x1=max(0,int(math.ceil(x1+.16*w)));x2=min(self.left.width,int(math.floor(x2-.16*w)))
        y1=max(0,int(math.ceil(y1+.15*h)));y2=min(self.left.height,int(math.floor(y2-.20*h)))
        if x2<=x1 or y2<=y1: return dict(result,reason='bbox_outside_image')
        roi=frame.disparity_px[y1:y2,x1:x2];mask=frame.valid_mask[y1:y2,x1:x2]
        values=roi[mask];area=roi.size
        result.update(valid_pixel_count=int(len(values)),valid_fraction=round(len(values)/area,4))
        if len(values)<self.min_pixels: return dict(result,reason='insufficient_stereo_matches')
        # Consensus in disparity space rejects background and isolated false matches.
        hist,edges=np.histogram(values,bins=np.arange(0,self.num_disparities+1,1.))
        smoothed=np.convolve(hist,[1.,2.,1.],mode='same')
        peak_index=int(np.argmax(smoothed));peak=float(edges[peak_index]+.5)
        tolerance=max(1.,.06*peak)
        inliers=mask & (np.abs(roi-peak)<=tolerance)
        selected=roi[inliers]
        if len(selected)<self.min_pixels or len(selected)/len(values)<.18:
            return dict(result,reason='ambiguous_disparity_clusters')
        ys,xs=np.nonzero(inliers);u=float(np.median(xs+x1));v=float(np.median(ys+y1))
        d=float(np.median(selected));effective_d=d-self.cx_difference
        if effective_d<=0: return dict(result,reason='nonpositive_corrected_disparity')
        z=self.fx*self.baseline/effective_d
        if not self.min_distance<=z<=self.max_distance: return dict(result,reason='outside_measurement_range')
        rectified_point=np.array([(u-self.cx)*z/self.fx,(v-self.cy)*z/self.fy,z])
        optical_point=self.left.r.T@rectified_point
        person_point=(self.person_from_optical@np.r_[optical_point,1.])[:3]
        forward,left,up=map(float,person_point)
        if forward<=0: return dict(result,reason='behind_person')
        sigma=max(.5,1.4826*float(np.median(np.abs(selected-d))))
        uncertainty=z*z*sigma/(self.fx*self.baseline)
        if uncertainty/z>.25: return dict(result,reason='depth_uncertainty_too_large')
        bearing,hour=clock_direction(forward,left)
        result.update(valid=True,reason=None,pixel_uv=[round(u,2),round(v,2)],disparity_px=round(d,4),
                      optical_xyz_m=optical_point.tolist(),person_xyz_m=person_point.tolist(),
                      forward_m=round(forward,3),distance_m=round(math.hypot(forward,left),3),
                      range_3d_m=round(float(np.linalg.norm(person_point)),3),
                      bearing_deg=round(bearing,2),clock_hour=hour,depth_m=round(z,3),
                      depth_uncertainty_m=round(uncertainty,3),inlier_pixels=int(len(selected)),
                      inlier_fraction=round(len(selected)/len(values),4))
        return result

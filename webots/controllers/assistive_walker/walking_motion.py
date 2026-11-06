"""Short-stride walking with planted stance feet and two-link leg IK."""
import math

STRIDE_M=.84
STANCE_FRACTION=.62
L1=math.hypot(.01,.46)
L2=math.hypot(-.062,.405)
A1=math.atan2(.01,.46)
A2=math.atan2(-.062,.405)


def foot_target(phase,blend=1.):
    phase%=1.
    travel=STRIDE_M*STANCE_FRACTION
    if phase<STANCE_FRACTION:
        x=travel*(.5-phase/STANCE_FRACTION);lift=0.
        pitch=-.06*math.exp(-phase/.07)+.09*max(0.,(phase-.50)/.12)
    else:
        s=(phase-STANCE_FRACTION)/(1-STANCE_FRACTION)
        tangent=-STRIDE_M*(1-STANCE_FRACTION)
        x=(2*s**3-3*s*s+1)*(-travel/2)+(s**3-2*s*s+s)*tangent+(-2*s**3+3*s*s)*(travel/2)+(s**3-s*s)*tangent
        lift=.075*math.sin(math.pi*s)**2
        pitch=-.12*math.sin(math.pi*s)
    return -.04+blend*(x+.04),blend*lift,blend*pitch


def leg_ik(ankle_x,ankle_z,foot_pitch):
    dx=ankle_x-(-.04);down=-.30-ankle_z
    reach=math.hypot(dx,down)
    reach=max(abs(L1-L2)+1e-5,min(L1+L2-1e-5,reach))
    beta=math.acos(max(-1.,min(1.,(reach*reach-L1*L1-L2*L2)/(2*L1*L2))))
    alpha=math.atan2(dx,down)+math.atan2(L2*math.sin(beta),L1+L2*math.cos(beta))
    hip=A1-alpha;knee=beta+A2-A1;ankle=foot_pitch-hip-knee
    return hip,knee,ankle


def walking_pose(distance_m,root_height,speed_mps):
    cycle=distance_m/STRIDE_M;blend=min(1.,max(0.,speed_mps/.18))
    result={}
    for side,offset,sole in [('left',0.,.108),('right',.5,.114)]:
        x,lift,pitch=foot_target(cycle+offset,blend)
        hip,knee,ankle=leg_ik(x,sole-root_height+lift,pitch)
        result[side+'LegAngle']=hip
        result[side+'LowerLegAngle']=knee
        result[side+'FootAngle']=ankle
    wave=math.sin(2*math.pi*cycle)
    result.update(leftArmAngle=.23*wave*blend,leftLowerArmAngle=-.16-.06*wave*blend,
                  leftHandAngle=.02,rightArmAngle=-.16,rightLowerArmAngle=-.28,
                  rightHandAngle=.02,headAngle=.012*wave*blend)
    return result


def forward_ankle(hip,knee):
    a=A1-hip;b=A2-hip-knee
    return -.04+L1*math.sin(a)+L2*math.sin(b),-.30-L1*math.cos(a)-L2*math.cos(b)

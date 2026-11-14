# 모듈 인터페이스

## 처리 경계

| 모듈 | 입력 | 출력 | 구현 |
| --- | --- | --- | --- |
| 시뮬레이터 | 월드·시나리오 | 동기 RGB, CameraInfo, 카메라 TF | Webots controller |
| 탐지 | 정류된 좌측 BGR 영상 | 클래스·bbox·confidence·선택적 ID | detection/base.py, yolo26.py |
| 깊이 | 동기 좌우 영상 + 탐지 영역 + 보정 | 객체별 3D·거리·방위각·유효 여부 | depth/base.py, stereo.py |
| 안내 | 유효한 객체 측정 | 시계 방향·한국어 문장·음성 | guidance/ |

탐지 결과는 반드시 **입력 영상의 촬영 시각**을 유지합니다. 추론을 끝낸 현재 시각으로 바꾸면 서로 다른 장면을 결합하게 됩니다. bbox는 정류된 좌측 영상의 픽셀 좌표입니다.

## ROS 토픽

| 토픽 | 메시지 | 의미 |
| --- | --- | --- |
| `/assistive/stereo/{left,right}/image_raw` | sensor_msgs/Image | 동기 BGRA8, 640×480 |
| `/assistive/stereo/{left,right}/camera_info` | sensor_msgs/CameraInfo | K/D/R/P |
| `/assistive/stereo/left/image_rect` | sensor_msgs/Image | YOLO26 입력용 정류 BGR 영상 |
| `/assistive/detections` | std_msgs/String JSON | 탐지 결과 |
| `/assistive/perception/objects` | std_msgs/String JSON | 영상 기반 객체별 거리·각도 |
| `/assistive/stereo/disparity_visualization` | sensor_msgs/Image | 시차 시각화 |
| `/assistive/guidance` | std_msgs/String JSON | 안내 문장과 측정 정보 |
| `/assistive/announcements` | std_msgs/String | 실제 발화 문장 |
| `/assistive/status` | std_msgs/String JSON | 시나리오·보행 상태 |
| `/clock`, `/tf` | 표준 ROS 메시지 | 촬영 시간과 좌표 변환 |
| `/assistive/ground_truth/objects` | std_msgs/String JSON | 데이터 수집·baseline 검증용 정답 |

기본 도메인은 71입니다. 카메라 주기는 시뮬레이션 시간 기준 64ms(15.625Hz)이며, 처리량이 부족하면 오래된 영상 쌍을 버립니다. YOLO 추론을 기다릴 스테레오 프레임 캐시는 파이프라인의 `depth.frame_cache_size`에서 설정합니다.

## 탐지 packet

```json
{
  "stamp_ns": 1024000000,
  "source": "yolo26",
  "coordinate_space": "rectified_left",
  "detections": [
    {"id": null, "class": "pedestrian", "bbox_xyxy": [210, 120, 305, 420], "confidence": 0.87}
  ]
}
```

`Detection.as_dict()`와 `validate_detection_packet()`가 좌표·면적·confidence·시각을 검증합니다. 시뮬레이터의 위치·거리 같은 추가 필드는 객체 데이터에서 제거합니다. 추적기를 붙이기 전에는 id를 만들지 않고 null로 유지합니다.

YOLO26 모드는 `/assistive/ground_truth/objects`를 구독하지 않습니다. baseline만 해당 토픽에서 이름과 bbox를 가져오며 `source=webots_box_adapter_NOT_yolo`를 명시합니다.

## 객체별 깊이 결과

성공: `valid=true`, `disparity_px`, `optical_xyz_m`, `person_xyz_m`, `depth_m`, `distance_m`, `forward_m`, `bearing_deg`, `clock_hour`, `depth_uncertainty_m`, 지지 픽셀 수를 포함합니다.

실패: `valid=false`, `reason`을 포함하고 **거리·3D 좌표를 만들지 않습니다**. 측정 실패는 탐지 실패와 구분합니다. 대표 표면의 거리이므로 물체 중심이나 전체 물체의 최소 여유 거리와 같지 않습니다.

좌표계:

- optical: 오른쪽 +X, 아래 +Y, 전방 +Z
- 보행자: 전방 +x, 왼쪽 +y, 위쪽 +z
- 방위각: 시계방향 양수, 정면 0°, 왼쪽 −30°는 11시, 오른쪽 +30°는 1시

촬영 시각의 TF를 먼저 사용하고, 없으면 `config/stereo_rig.json`의 설치 보정값을 사용합니다. 변환 출처는 `extrinsic_source`에 기록합니다. 이것은 카메라 설치 보정이며 대상의 정답 위치가 아닙니다.

목적지 임무·신호 이벤트는 [DESTINATION_MISSIONS.md](DESTINATION_MISSIONS.md)의 `/assistive/mission/events`, `/assistive/mission/alerts`, status의 `mission` 구조를 사용합니다. 이 데이터의 출처는 `scenario_script`이며 거리 추정 입력과 분리합니다.

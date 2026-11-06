# 보행 보조: 스테레오 거리·방향 알고리즘 + Webots 거리 환경

핵심 알고리즘은 [`perception/stereo.py`](perception/stereo.py)입니다. 좌우 카메라 영상에서 시차를 계산하고, 물체 표면의 3차원 위치를 보행자 좌표계로 변환해 **거리·각도·시계 방향**을 출력합니다. 거리 계산에 시뮬레이터의 물체 위치를 사용하지 않습니다.

현재 **물체 이름과 bbox는 Webots 임시 어댑터**가 공급합니다. YOLO 학습/추론은 아직 연결하지 않았습니다. YOLO가 정류된 좌측 영상에서 이름과 bbox를 제공하면 동일한 스테레오 알고리즘에 연결할 수 있습니다. 원본 정답 토픽은 데이터 수집·검증용으로 별도 유지합니다.

## 실행

이 PC의 Webots R2025a, ROS 2 Humble, `/usr/bin/python3`, numpy/OpenCV/Pillow, `libespeak-ng`, `paplay` 설치를 사용합니다.

```bash
cd /home/boss/cv
./webots/scripts/start_demo.sh
./webots/scripts/stop_demo.sh
```

`start_demo.sh`는 Webots, 임시 bbox 어댑터, 스테레오 추정, 영상 모니터, 한국어 음성을 실행합니다. 기본 ROS_DOMAIN_ID=71, Webots 포트=1241입니다. `WEBOTS_BIN`으로 실행 경로를 바꿀 수 있습니다.

모니터 또는 Webots의 `P`로 보행을 멈추고 다시 시작합니다. Webots의 `R`은 경로 재시작, `V`는 외부 관찰 시점의 보행자 추적 전환, 모니터의 `Q`는 모니터만 종료합니다. 일시정지 시 보행 속도를 완만하게 줄입니다. Webots 화면에 키보드 포커스가 있을 때 키가 동작합니다.

## 거리와 각도를 구하는 핵심

1. 같은 타임스탬프의 좌우 RGB 영상과 `CameraInfo`를 받습니다.
2. K/D/R/P를 이용해 왜곡을 보정하고 영상을 정류합니다.
3. StereoSGBM과 좌우 일치 검사로 유효 시차를 계산합니다.
4. 물체 bbox 안에서 일관된 시차를 가진 표면을 찾습니다.
5. `Z = fx × baseline / corrected_disparity`로 깊이를 복원합니다.
6. 픽셀 좌표를 3D로 역투영하고 카메라→보행자 외부 보정값으로 변환합니다.
7. 보행자 기준 수평 거리, 방위각, 시계 방향을 구해 한국어 문장으로 만듭니다.

측정에 실패하면 `valid=false`와 원인을 출력하며 거리나 좌표를 만들어 채우지 않습니다. 알고리즘·수식·입출력·한계는 [`docs/STEREO_ALGORITHM.md`](docs/STEREO_ALGORITHM.md)를 참고하세요.

현재 카메라는 640×480, 수평 FOV 65°, baseline 0.12m, 하향각 0.12rad입니다. 명목 눈높이는 약 1.615m이고 보행 중 조금 움직입니다. ROS TF에서 **촬영 시점의 카메라→사람 변환**을 받아 반영하며, 없으면 `webots/config/stereo_rig.json`의 설치 보정값을 사용합니다. 객체의 정답 위치와 카메라 설치 보정은 별개입니다.

음성 예: “11시 방향, 3미터 앞에 입간판이 있습니다.” 수평 거리를 0.5m 단위로 반올림하고, 6m 이내의 유효한 대상 중 가까운 대상을 최소 5초 간격으로 안내합니다. 음성은 기존 espeak-ng 한국어 음성으로 오프라인 재생합니다.

## 현실의 어려움을 넣은 환경

약 40m 길이의 상가 앞 보도에 보도블록, 점자블록, 도로·횡단보도, 간판·차양·유리창, 가로수, 주차 차량을 배치했습니다. 무작위 객체를 많이 쌓지 않고 다음 상황을 간격을 두어 보여줍니다.

| 구간 | 상황 |
| --- | --- |
| 상가 앞 | 벤치, 가로수 그림자, 배경의 복잡한 직선과 질감 |
| 입간판 | 통로로 나온 입간판 뒤에 일부 가려진 낮은 말뚝 |
| 가로등 | 배경과 색이 비슷한 가느다란 기둥 |
| 공사 | 콘·펜스로 줄어든 보행 공간 |
| 횡단 | 보행자가 주차 차량 주변에서 보도를 가로지름 |
| 차량 진입부 | 포장 질감, 낮아진 경계석, 점자 경고 블록 |

장애물은 제자리에 있고, 예전처럼 구간마다 시야 밖으로 숨기지 않습니다. 정답 인식 범위는 7.5m입니다. 객체 수를 일정하게 만드는 필터로 난도를 숨기지 않습니다.

보행은 짧은 보폭(한 주기 약 0.84m), 바닥을 딛는 발의 위치 유지, 2링크 다리 역기구학, 완만한 가감속·회전, 상하 움직임, 지팡이 탐색을 사용합니다. 기본 요청 속도는 0.72m/s이며 좁은 구간에서 감속합니다. 횡단 보행자 앞에서는 잠시 정지합니다. **동선과 감속은 연출을 위한 사전 설정이며 영상 인식 기반의 자율 회피는 아닙니다.** 끝에 도달하면 시작점으로 순간 복귀해 반복합니다.

## ROS 인터페이스

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=71
ros2 topic echo /assistive/perception/objects
ros2 topic echo /assistive/announcements
ros2 topic pub --once /assistive/voice_enabled std_msgs/msg/Bool '{data: false}'
```

| 토픽 | 내용 |
| --- | --- |
| `/assistive/stereo/{left,right}/image_raw` | 좌우 BGRA8 영상, 64ms 주기(시뮬레이션 기준 15.625Hz) |
| `/assistive/stereo/{left,right}/camera_info` | K/D/R/P, 우측 P[3]=−fx×baseline |
| `/assistive/stereo/left/image_rect` | 정류된 좌측 BGR 영상, 추후 YOLO 입력 |
| `/assistive/detections` | 이름·bbox·촬영 시각 JSON. 현재 임시 어댑터가 공급 |
| `/assistive/stereo/disparity_visualization` | 시차 색상 영상, 일치 검사에서 탈락한 픽셀은 검정 |
| `/assistive/perception/objects` | 영상 기반 깊이·3D·수평 거리·각도·시계 방향·유효 여부 |
| `/assistive/guidance` | 유효한 스테레오 측정값으로 만든 한국어 안내 |
| `/assistive/announcements` | 실제 발화 문장, std_msgs/String |
| `/assistive/status` | 보행 위치·속도·구간 정보 JSON |
| `/clock`, `/tf` | 시뮬레이션 시간, 사람·카메라 좌표계 |
| `/assistive/pause`, `/assistive/speed` | Bool 정지 요청 / Float32 속도 요청 |
| `/assistive/voice_enabled` | Bool 음성 켜기/끄기 |
| `/assistive/ground_truth/objects` | 학습·검증용 Webots 정답. 거리 알고리즘의 입력이 아님 |

실제 시간의 영상 FPS는 컴퓨터 성능에 따라 낮아집니다. 스테레오 노드는 처리량을 초과하면 오래된 프레임을 버리고 가장 최근의 동기 쌍을 처리합니다.

## 검증

```bash
cd /home/boss/cv
/usr/bin/python3 -m unittest discover -s tests -v
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=71
/usr/bin/python3 webots/scripts/check_streams.py
/usr/bin/python3 webots/scripts/validate_runtime.py --seconds 90
```

합성 시차로 3m·6m 복원, 좌우 주점 차이 보정, 보행자 좌표 변환·시계 방향, 무늬 없는 영상 거부, 역방향 baseline 거부, 화면 밖 bbox 거부, 발 디딤·다리 IK를 검사합니다. 실행 검증은 bbox 입력에 정답 거리/좌표가 섞이지 않는지도 확인합니다. 정밀도에 대한 실제 거리 벤치마크 전체를 검증한 것은 아닙니다.

## 학습용 데이터 수집

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=71
/usr/bin/python3 webots/scripts/capture_dataset.py --count 100 --interval 0.5
```

`datasets/sidewalk/<실행시각>/` 아래 `images/`, `right_images/`, `labels/`, `metadata/`, `classes.txt`를 저장합니다. 좌/우 영상과 정답 시각이 같은 경우만 저장합니다. 클래스는 `webots/config/object_classes.json`에서 관리합니다. 현재 0=bench, 1=traffic_cone, 2=pedestrian, 3=signboard, 4=bollard, 5=pole, 6=barrier, 7=car입니다. 라벨은 시뮬레이터 bbox이므로 검수해야 합니다. 서로 다른 배치·조명·실행을 train/val/test로 분리하는 작업과 YOLO 학습은 별도입니다.

## 수정 위치

- `perception/stereo.py`: ROS/Webots에 의존하지 않는 핵심 알고리즘
- `perception/ros_node.py`: 영상·보정값·bbox·촬영시점 TF 연결
- `webots/scripts/build_world.py`, `build_textures.py`: 거리와 텍스처 생성
- `webots/config/urban_scene.json`: 동선·구간 설정
- `webots/config/walker_rig.wbt.inc`, `stereo_rig.json`: 리그 형상·외부 보정
- `webots/controllers/assistive_walker/walking_motion.py`: 발 궤적·다리 IK
- `webots/scripts/sim_detection_adapter.py`: 임시 이름/bbox 어댑터
- `webots/logs/`: 최신 영상, 실행·측정·검증 로그와 발화 WAV

월드 변경 후 `/usr/bin/python3 webots/scripts/build_world.py`로 재생성하고 데모를 재시작합니다. 원본과 자산별 라이선스는 [THIRD_PARTY.md](THIRD_PARTY.md)에 기록했습니다.

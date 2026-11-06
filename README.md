# 시각장애인 보행 보조: Webots + Stereo Vision

Webots에서 흰지팡이를 든 사람이 걷고, 눈높이의 좌우 카메라 영상을 ROS 2로 발행하는 초기 시뮬레이션입니다. `webots/` 안에서 월드, 컨트롤러, 실행 스크립트를 관리합니다.

현재 동작: 보행 애니메이션, 스테레오 RGB, 보정 정보와 TF, 구간별 벤치/교통 콘/사람, 방향·거리 표시, 오프라인 한국어 음성 안내, 학습 데이터 수집.

**현재 물체 이름·거리·음성의 입력은 Webots 정답 데이터입니다. YOLO 학습·추론과 스테레오 영상 기반 거리 추정은 아직 구현하지 않았습니다.** 일반적인 보행 경로를 재생하는 데모이며 장애물을 인식해 스스로 회피하는 시스템은 아닙니다.

## 실행

환경: Ubuntu, Webots R2025a, ROS 2 Humble, 시스템 `/usr/bin/python3`, numpy/OpenCV/Pillow, `libespeak-ng`, `paplay`. 이 PC의 기존 설치를 사용합니다.

```bash
cd /home/boss/cv
./webots/scripts/start_demo.sh
# 종료
./webots/scripts/stop_demo.sh
```

개별 실행은 `run_sim.sh`, `run_viewer.sh`, `run_voice.sh`입니다. Webots 경로를 바꾸려면 `WEBOTS_BIN`을 지정합니다. 기본 ROS_DOMAIN_ID는 **71**로, 다른 ROS 작업과 분리합니다. Webots 외부 컨트롤러 포트는 1241입니다.

Webots 화면 또는 영상 모니터에서 `P`로 보행 일시정지/재개합니다. Webots 화면에서 `R`로 경로를 처음부터 재생합니다. 모니터의 `Q`는 모니터 창만 닫습니다.

보행 속도는 0.65 m/s이며 각 대상 전방에서 2.5초 머뭅니다. 약 25.5m 진행하면 시작점으로 순간 복귀해 반복합니다. 혼잡하지 않은 초기 학습 환경을 위해 x 구간 0–8m, 8–16m, 16m 이후에 각각 벤치, 콘, 사람만 보이게 합니다. 비활성 대상은 시야 밖으로 이동시킵니다. 카메라 외부 관찰 화면은 보행자를 따라갑니다.

## 카메라와 ROS 토픽

카메라는 보행자 몸에 고정된 눈높이 리그에 장착합니다. 전방 +X, 좌측 +Y, 위쪽 +Z입니다. 해상도 640×480, 수평 FOV 65°, 기준 높이 1.67m, 하향각 0.12rad, baseline 0.12m, 동기 영상 주기 64ms(시뮬레이션 시간 기준 15.625Hz)입니다. 실행 장치 성능에 따라 실제 시간의 FPS는 낮아질 수 있습니다.

| 토픽 | 용도 |
| --- | --- |
| `/assistive/stereo/left/image_raw` | 좌측 BGRA8 원본 영상 |
| `/assistive/stereo/right/image_raw` | 우측 BGRA8 원본 영상 |
| `/assistive/stereo/left/camera_info` | 좌측 K, D, R, P |
| `/assistive/stereo/right/camera_info` | 우측 보정 정보, P[3] = −fx × 0.12 |
| `/clock`, `/tf` | 시뮬레이션 시계, world/base/optical 좌표계 |
| `/assistive/status` | 보행 상태 JSON |
| `/assistive/ground_truth/objects` | Webots 정답 클래스·위치·bbox JSON |
| `/assistive/ground_truth/guidance` | 정답 기반 시계 방향·수평 거리·한국어 문장 JSON |
| `/assistive/announcements` | 실제 발화 문장, std_msgs/String |
| `/assistive/pause` | 보행 정지 여부, std_msgs/Bool |
| `/assistive/speed` | 속도 0–1.2m/s, std_msgs/Float32 |
| `/assistive/voice_enabled` | 음성 켜기/끄기, std_msgs/Bool |

토픽을 터미널에서 확인할 때:

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=71
ros2 topic list
ros2 topic echo /assistive/announcements
ros2 topic pub --once /assistive/voice_enabled std_msgs/msg/Bool '{data: false}'
```

## 방향·거리 안내

카메라 중앙을 12시, 좌측을 11시·10시, 우측을 1시·2시로 표현하며 수평 방위각을 30° 구간으로 반올림합니다. 현재 65° 시야에서는 주로 11시/12시/1시가 나옵니다. `guidance.py`가 카메라 하향각을 보정한 뒤 카메라에서 물체 bounding box 중심까지의 **수평 거리**를 계산합니다. 가장 가까운 표면까지의 여유 거리는 아닙니다.

예: “11시 방향, 3미터 앞에 벤치가 있습니다.” 음성에서는 0.5m 단위로 반올림하고, 6m 이내의 가장 가까운 대상을 최소 5초 간격으로 안내합니다. 물체·방향·0.5m 구간이 바뀌었을 때 다시 안내합니다. 음성은 네트워크 없이 기존 espeak-ng 한국어 음성으로 재생합니다. 음질은 로봇 음성 수준입니다.

## YOLO용 데이터 수집

시뮬레이터가 실행 중일 때:

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=71
/usr/bin/python3 webots/scripts/capture_dataset.py --count 100 --interval 0.5
```

`datasets/sidewalk/<실행시각>/` 아래에 좌측 `images/`, 우측 `right_images/`, 좌측 YOLO 형식 `labels/`, 정답 메타데이터 `metadata/`, `classes.txt`를 저장합니다. 좌/우 영상과 정답의 시뮬레이션 타임스탬프가 일치할 때만 저장합니다. 클래스는 0=bench, 1=traffic_cone, 2=pedestrian입니다. bbox는 Webots가 제공한 경계 상자이므로 검수해야 합니다.

현재 단일 월드의 반복 영상만으로 실제 환경 성능을 검증할 수 없습니다. 다음 학습 단계에서는 배치·외형·조명·배경을 바꾸어 수집하고, 서로 다른 실행/장면을 train/val/test로 분리해야 합니다. 현재 수집 도구는 분할이나 모델 학습을 수행하지 않습니다.

## 파일 위치

- `webots/worlds/assistive_sidewalk.wbt`: 실제 실행 월드
- `webots/scripts/build_world.py`: 월드 생성 원본. 수정 후 실행하여 재생성
- `webots/controllers/assistive_walker/assistive_walker.py`: 보행·카메라·ROS 브리지
- `webots/scripts/stereo_viewer.py`: ROS 좌우 영상과 안내 표시
- `webots/scripts/guidance.py`, `voice_guidance.py`, `korean_tts.py`: 방향·거리·음성
- `webots/logs/`: 실행 로그, 최신 좌우 이미지, 발화 WAV/JSONL

## 원본과 라이선스

공식 [cyberbotics/webots R2025a Pedestrian](https://github.com/cyberbotics/webots/tree/R2025a/projects/humans/pedestrian)를 사용했습니다. 세부 출처와 자산별 라이선스는 [THIRD_PARTY.md](THIRD_PARTY.md)에 기록했습니다. 모델 파일을 로컬에 포함해 실행 시 GitHub 다운로드가 필요 없습니다.

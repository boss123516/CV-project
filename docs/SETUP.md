# 설치와 실행

## 지원 기준

기준 환경은 Ubuntu 22.04 / Python 3.10 / ROS 2 Humble / Webots R2025a입니다. Python 패키지 설치는 저장소의 가상환경에 하고, ROS 2 Python 바인딩은 시스템 설치를 사용합니다. 현재는 **저장소 clone + editable 설치**를 기준으로 하며, 리소스를 모두 포함한 독립 wheel 배포는 지원 범위가 아닙니다.

## 1. 시스템 준비

ROS 2 Humble과 Webots R2025a를 설치하고, 필요한 시스템 도구를 준비합니다.

```bash
sudo apt install python3-venv libgl1 fonts-noto-cjk espeak-ng pulseaudio-utils
source /opt/ros/humble/setup.bash
```

영상 모니터와 Webots GUI에는 데스크톱 디스플레이가 필요합니다. SSH 세션에서는 사용할 디스플레이 또는 가상 디스플레이를 별도로 준비해야 합니다. 음성은 Linux의 libespeak-ng와 paplay를 사용합니다. 음성을 사용하지 않으면 `--no-voice`를 지정합니다.

## 2. Python 환경

```bash
./scripts/setup.sh --yolo
.venv/bin/python scripts/download_models.py
./scripts/doctor.sh --pipeline yolo26
```

`--system-site-packages`로 가상환경을 만들어 시스템 rclpy를 재사용합니다. ROS 2 자체는 PyPI requirements에 넣지 않습니다. 핵심 알고리즘 테스트만 하려면 `python3 -m pip install -e .`로 충분합니다. YOLO 추론에는 `python3 -m pip install -e '.[yolo]'`가 필요합니다.

체크포인트는 명시적인 다운로드 명령으로만 준비합니다. 저장소에는 모델 바이너리를 넣지 않습니다. 프로젝트 클래스용 가중치를 학습하면 설정의 `detector.weights`를 해당 경로로 바꿉니다.

## 3. 경로 설정

```bash
export WEBOTS_BIN=/path/to/webots/webots
export ROS_SETUP=/opt/ros/humble/setup.bash
# 필요할 경우에만 지정
export CV_PYTHON=/path/to/python
export ROS_DOMAIN_ID=71
```

Webots는 `WEBOTS_BIN`, PATH의 `webots`, `WEBOTS_HOME/webots`, `~/.ros/webotsR2025a/webots/webots` 순서로 찾습니다. 개발자 홈 디렉터리 경로를 코드에 고정하지 않습니다. 실행 파일은 항상 직접 지정할 수 있습니다.

## 4. 실행

```bash
./scripts/run.sh --pipeline baseline --scenario urban_baseline
./scripts/stop.sh
./scripts/run.sh --pipeline yolo26 --scenario crossing_pedestrian
```

실행 구성은 `webots/logs/run.json`, 각 프로세스의 로그는 같은 폴더의 `sim.log`, `detector.log`, `perception.log`, `viewer.log`, `voice.log`에 기록합니다. `CV_RUN_DIR`로 런타임 저장 위치를 바꿀 수 있습니다.

```bash
source scripts/env.sh
python3 -m cv_project status
```

다른 파이프라인·시나리오를 시작하려면 먼저 종료해야 합니다. 시작 시 모델 파일이 없으면 오류를 반환하며 임시 정답 탐지기로 자동 전환하지 않습니다.

## 5. 월드 재생성·데이터 수집

```bash
source scripts/env.sh
"$CV_PYTHON" webots/scripts/build_world.py
"$CV_PYTHON" webots/scripts/capture_dataset.py --count 100 --interval 0.5
```

월드와 텍스처는 이미 포함되어 있으므로 보통 재생성이 필요 없습니다. 수정 후에는 월드를 재생성하고 데모를 재시작합니다. 데이터는 `datasets/`에 저장하며 Git에서 제외합니다. 클래스 이름은 `config/object_classes.json`에서 관리합니다. 캡처 도구는 좌우 영상과 정답 시각이 같은 경우만 저장합니다.

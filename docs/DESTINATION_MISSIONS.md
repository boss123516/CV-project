# 목적지 이동·우회·신호등 시나리오

기존 직진 거리의 구간 설정 여섯 개에 더해, **서로 다른 월드 네 개**를 추가했습니다. 가게 이름과 메뉴 문구를 없애고 주거동, 중정, 출입구, 도로·횡단보도 중심으로 구성했습니다.

| ID | 환경·목적지 | 연출 |
| --- | --- | --- |
| `residential_detour` | 주거 골목 → 주거동 출입구 | 펜스에 지팡이가 닿음 → 후진 → 좌우 확인 → 옆 골목 우회 → 모퉁이를 돌아 도착 |
| `courtyard_detour` | 공동주택 중정 → 공동현관 | 낮은 화단 접촉 → 후진 → 화단 우회 → 보행자 대기 → 현관 접근 |
| `station_access_detour` | 역 앞 광장 → 역사 출입구 | 횡단 보행자에게 양보 → 막힌 진입로 접촉 → 옆 접근로 우회 |
| `signalized_crossing` | 신호등 횡단보도 → 건너편 보도 | 빨간불 접근 → 차량 통행 중 정지·음성 → 초록불과 차량 비움 확인 → 횡단 |

```bash
./scripts/run.sh --pipeline yolo26 --scenario residential_detour
./scripts/stop.sh
./scripts/run.sh --pipeline yolo26 --scenario signalized_crossing
```

커스텀 클래스 학습 전에는 `--pipeline baseline`으로 동일한 장면을 재현할 수 있습니다. 탐지 backend와 상관없이 목적지 이동·교통 연출은 시나리오 계층에서 실행합니다.

## 자연스러운 동선

`cv_project/simulation/trajectory.py`가 구간들을 C1 연속 Hermite 곡선으로 이어 줍니다. 모퉁이마다 멈춰 90도로 방향을 바꾸는 대신 곡선을 걸으며 회전하고, 곡률에 따라 속도를 줄입니다. 연속된 이동·우회 행동 사이에서도 속도를 이어 갑니다. 후진·접촉·좌우 탐색·도착 대기는 별도 행동입니다.

`mission.py`의 상태는 `walk`, `contact`, `backtrack`, `scan`, `detour`, `wait`, `signal_wait`, `arrive`입니다. 목적지에 도착하면 잠시 머문 뒤 반복합니다. `P`는 정지/재개, `R`은 임무 재시작, `V`는 외부 시점 추적 전환입니다.

## 접촉과 우회가 의미하는 것

접촉은 지팡이 끝이 장애물에 닿는 상황을 연출한 **scripted cane tap**입니다. 사람 몸을 장애물 속으로 밀거나 실제 물리 충격을 측정했다고 주장하지 않습니다. 시험에서는 몸의 중심이 장애물 경계에서 떨어져 있는지 확인합니다.

동선·우회 선택은 `scenarios/<id>/scene.json`에 정의한 스크립트입니다. YOLO/스테레오 결과로 경로를 계획하는 자율 회피는 아직 아닙니다. 영상 기반 탐지·거리 추정 파이프라인은 별도로 계속 실행되므로, 추후 해당 결과로 동선을 제어하는 모듈을 붙일 수 있습니다.

## 빨간불·초록불과 차량

`traffic.py`가 보행 신호와 두 차량의 움직임을 제어합니다. 빨간 보행 신호 구간에는 차량이 약 5.4–5.8m/s로 통행합니다. 보행자는 경계석 앞에 정지합니다. 차량을 감속·정지시킨 뒤 보행 신호를 초록불로 바꾸고, 횡단 구간이 비어 있어야 횡단을 허용합니다. 보행자가 아직 횡단 중이면 보호 시간을 유지합니다.

- 빨간불 안내: **“빨간불입니다. 기다리세요.”**
- 초록불 안내: **“초록불로 바뀌었습니다. 차량이 멈춘 것을 확인하고 건너세요.”**

초록불 안내 후 짧게 기다렸다가 이동합니다. 이 신호 상태의 출처는 **`scenario_script`**입니다. 현재 신호 색상을 영상으로 판정했다고 주장하지 않습니다. YOLO26이 제공하는 신호등 bbox와 색상 판정은 별개의 기능이며, 실제 영상 기반 신호 판정기는 후속 모듈로 추가해야 합니다.

현재 YOLO26 설정에는 프로젝트 클래스 allowlist를 넣어 범위 밖 COCO 클래스는 전달하지 않습니다. 범위 밖 오탐을 차량 등으로 바꾸어 표시하지 않으며, 차종·장애물 전체의 탐지 정확도는 커스텀 학습으로 개선해야 합니다.

## 화면과 이벤트

영상 모니터 오른쪽에 목적지, 현재 행동, 남은 직선 거리, 동선 지도, 보행 신호를 표시합니다. 남은 직선 거리는 우회 중 증가할 수 있습니다. 지도는 시나리오 메타데이터이며 SLAM 결과가 아닙니다.

| 토픽 | 내용 |
| --- | --- |
| `/assistive/status`의 `mission` | 단계·목적지·접촉 횟수·도착 여부·지도·교통 상태 |
| `/assistive/mission/events` | `staged_cane_contact`, `detour_started`, `destination_reached`, 빨간불 대기·초록불 이벤트 |
| `/assistive/mission/alerts` | 출처를 포함한 신호 안내 JSON |
| `/assistive/announcements` | 실제 발화 문장 |

차량·신호·접촉 이벤트에는 출처를 기록하고, 그 값을 스테레오 깊이 알고리즘에 넘기지 않습니다.

## 재생성과 검증

```bash
source scripts/env.sh
"$CV_PYTHON" webots/scripts/build_world.py
"$CV_PYTHON" webots/scripts/build_mission_worlds.py
"$CV_PYTHON" -m unittest discover -s tests -v
"$CV_PYTHON" webots/scripts/validate_mission.py --scenario signalized_crossing --seconds 100
```

순수 알고리즘 시험은 곡선 연결·회전 속도, 장애물 여유 공간, 후진·우회·목적지 도착, 빨간불 정지, 차량 비움, 정지 시 교통 시간 동결을 검사합니다. 실행 검증은 실제 Webots 상태와 이벤트를 받아 도착 여부를 확인합니다.

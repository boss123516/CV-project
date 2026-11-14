# 단계적으로 확장하는 방법

## YOLO26 커스텀 모델

1. `config/object_classes.json`의 프로젝트 클래스에 맞는 학습 데이터를 준비합니다.
2. YOLO26을 별도로 fine-tuning합니다. 현재 저장소가 자동으로 학습을 시작하지는 않습니다.
3. `models/` 아래 체크포인트를 놓고 `config/pipelines/yolo26.json`의 `detector.weights`를 지정합니다.
4. 클래스 이름을 바꾸어야 하면 `class_map`을 설정합니다. 기본값은 COCO의 `person`을 프로젝트의 `pedestrian`으로 바꿉니다.
5. 기존 깊이·안내 모듈을 수정하지 않고 같은 실행 명령으로 검증합니다.

다른 탐지기를 붙이려면 `Detector.detect(image_bgr)`가 `Detection` 목록을 반환하도록 구현하고 detection 노드의 backend 선택에 등록합니다. 추적기는 id를 채울 수 있습니다. 거리와 객체 크기는 탐지 계약에 넣지 않습니다.

## 새로운 객체별 스테레오 알고리즘

현재 `depth/stereo.py`는 SGBM 기준 구현입니다. `DepthEstimator` 계약은 다음과 같습니다.

- `compute(left_image, right_image)`: 동기 영상에서 정류 영상·시차/유효 픽셀을 계산
- `localize(frame, detection)`: 객체 ROI별 위치·거리·각도와 유효 여부 반환
- 공통 상태: baseline, fx, num_disparities, person_from_optical
- 성공·실패 결과는 기존 객체 출력 계약을 유지

구현 클래스를 `cv_project/depth/factory.py`의 `BACKENDS`에 등록하고 파이프라인의 `depth.backend`를 선택합니다. ROI 매칭, instance mask 기반 표면 선택, 시간 필터 등을 추가할 때 detector·guidance를 바꾸지 않도록 이 경계를 유지합니다. 현재 시차 시각화는 `StereoFrame`의 표준 필드를 사용합니다.

알고리즘 변경 시 정답값은 **평가 프로세스에서만** 읽습니다. 파이프라인 안에서 측정에 실패했다고 정답 깊이로 채우면 알고리즘 성능을 검증할 수 없습니다.

## 시나리오 추가

현재 여섯 시나리오는 `webots/worlds/assistive_sidewalk.wbt`를 공유합니다. `scenarios/<id>/scenario.json`을 복사해 새 ID를 만들고 시작·종료 위치와 속도, 목표 클래스를 설정합니다.

```json
{
  "id": "my_scenario",
  "title_ko": "새로운 검증 구간",
  "version": 1,
  "world": "webots/worlds/assistive_sidewalk.wbt",
  "scene": "scenarios/urban_baseline/scene.json",
  "route": {"start_m": 7, "end_m": 14, "cruise_speed_mps": 0.55},
  "evaluation": {"target_classes": ["signboard", "bollard"], "max_visible_targets": 5}
}
```

```bash
./scripts/run.sh --pipeline baseline --scenario my_scenario
```

서로 다른 월드를 만들 때는 `world`를 새 `.wbt`로 지정하고 `scene`에 실제 경로를 둡니다. 공통 scene은 `path_xy`, 단계별 `scenarios`, route 범위를 정의합니다. 기준 controller를 재사용한다면 `OVERVIEW`, `WALKER`, `CANE_SWEEP`, `TARGET_PERSON`, 좌우 Camera DEF와 장치 이름이 필요합니다. 새로운 인물·차량 행동은 controller 계층에 추가합니다.

기준 월드의 geometry 생성은 `webots/scripts/build_world.py`, 텍스처 생성은 `build_textures.py`, 카메라 리그 형상은 `webots/config/walker_rig.wbt.inc`에 있습니다. 리그를 바꾸면 `config/stereo_rig.json`과 CameraInfo/TF도 함께 맞춥니다. 단순히 프로필 JSON만 추가한다고 새로운 geometry가 생기지는 않습니다.

## 앞으로의 권장 평가 항목

클래스별 탐지 precision/recall, 거리 구간별 오차, 방위각 오차, 가림 비율별 유효 깊이 비율, 측정 지연, 안내 반복률을 서로 분리해 기록합니다. 무늬 없는 표면·역광·반사·동적 가림·화면 가장자리 등에서 실패를 숨기지 않도록 데이터셋과 시나리오를 분리합니다.

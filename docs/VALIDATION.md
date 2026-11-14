# 검증 기록

2026-11-14 로컬 환경에서 확인한 통합 범위입니다. 커스텀 클래스 학습 정확도나 실제 보행 환경의 전체 성능을 검증한 결과는 아닙니다.

## 핵심·모듈 테스트

`python3 -m unittest discover -s tests -v`: **18개 통과**.

- 알려진 합성 시차에서 3m·6m 복원, 좌우 주점 차이 보정
- 보행자 기준 좌표 변환, 좌우 방위각·시계 방향
- 무늬 없는 영상, 잘못된 baseline, 화면 밖 bbox 거부
- 발 디딤 유지·다리 역기구학
- 탐지 계약 검증, 시뮬레이터 거리·위치 필드 제거
- YOLO 어댑터 출력 매핑과 누락된 가중치 오류
- 여섯 시나리오의 월드·실행 범위, 두 파이프라인 설정

GitHub Actions는 ROS/Webots GUI 없이 위 테스트와 compile 검사를 실행하도록 구성했습니다. 원격 CI 실행 결과는 Actions에서 별도로 확인합니다.

## Webots 재현 모드

`baseline + occluded_sign` 조합으로 Webots, simulator bbox adapter, stereo depth, viewer를 실행했습니다. 보행 상태에 `scenario_profile=occluded_sign`이 기록되고 7–14m 경로를 반복하는 것을 확인했습니다. 임시 탐지 어댑터는 깊이·물체 좌표를 전달하지 않습니다.

## 실제 YOLO26 → 스테레오 연결

Ultralytics 8.4.46과 사전학습 `yolo26n.pt`를 사용해 `yolo26 + crossing_pedestrian` 조합을 실행했습니다.

- 확인 구간: 출력 packet 60개
- 실제 YOLO 탐지: 30개
- 유효한 스테레오 위치 추정: 22개
- 해당 확인 구간의 클래스: pedestrian
- 출력의 detector_source: yolo26
- 해당 detector 노드는 정답 객체 토픽을 구독하지 않음

이는 연결·형식·유효 측정 여부에 대한 smoke test입니다. 30개 탐지 중 22개라는 수치를 데이터셋 recall이나 전체 정확도로 해석하면 안 됩니다. 예제 체크포인트는 프로젝트 장애물 전체를 학습하지 않았으며, 새 장면에서는 탐지 결과가 없을 수 있습니다.

원본 실행 로그와 체크포인트는 `webots/logs/`, `models/`에 로컬로 보관하며 Git에 포함하지 않습니다. 실제 체크포인트로 단일 영상 추론 호출도 별도로 확인했습니다.


## 목적지·곡선 우회·교통 환경 추가 검증

추가 수정 후 순수 테스트는 **26개 통과**했습니다. 새 테스트는 곡선 연결, 연속 방위각, 몸과 장애물의 간격, 접촉 후 후진·우회·도착, 빨간불 대기와 차량 비움, 일시정지 시 교통 시간 동결을 검사합니다.

Webots 실제 실행으로 residential_detour, courtyard_detour, station_access_detour의 접촉·후진·탐색·우회·도착을 확인했습니다. signalized_crossing에서는 빨간불 대기와 초록불 전환, 최대 5.8m/s 차량 통행, 횡단 구간이 비어 있는 상태의 횡단 및 도착을 확인했습니다. 신호·접촉·우회는 scenario_script 출처이며 영상 판정 성능 지표로 계산하지 않습니다.

기존 검사 기록의 테스트 18개는 이전 모듈화 시점의 결과입니다. 추가 실행 원본은 webots/logs/validation_<scenario>.json에 로컬 보관합니다.

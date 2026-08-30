# TCSpy 코드 참조 문서 (인덱스)

> 전체 코드베이스를 다시 읽지 않고 구조·클래스·메서드·설정 키를 참조하기 위한 문서.
> 2026-08-06 전체 코드 정독 기준으로 작성됨. 코드 수정 시 해당 모듈 문서도 함께 갱신할 것.

## 문서 구성

| 문서 | 내용 |
|---|---|
| [CODE_REFERENCE_configuration.md](CODE_REFERENCE_configuration.md) | `mainConfig`, 전체 설정 키 인벤토리, `interfaces/` |
| [CODE_REFERENCE_devices.md](CODE_REFERENCE_devices.md) | `SingleTelescope`, `MultiTelescopes`, `TelescopeStatus`, `pwi4_client`, observer/switch 등 |
| [CODE_REFERENCE_action.md](CODE_REFERENCE_action.md) | 액션 공통 패턴, `MultiAction`, level1/2/3 전체 액션 |
| [CODE_REFERENCE_applications.md](CODE_REFERENCE_applications.md) | `NightObservation`, `AppScheduler`, `Startup`/`Shutdown`, 캘리브레이션 앱 |
| [CODE_REFERENCE_utils.md](CODE_REFERENCE_utils.md) | `NightSession`, `Timeout`, connector 4종, logger, `mainImage`, `DataTransferManager`, 예외 목록 |
| [CODE_REFERENCE_databases.md](CODE_REFERENCE_databases.md) | 타겟 DB (`Dynamic`/`RIS`/`IMS`/`Program`), 스코어링/스케줄링, `Tiles`, `SingleTarget`/`MultiTargets` |
| [CODE_REFERENCE_alertmanager.md](CODE_REFERENCE_alertmanager.md) | ToO 알림 파이프라인 (`Alert`/`AlertBroker`/`AlertMonitor`) |

---

## 전체 아키텍처

TCSpy = Telescope Control System with Python. 7DT 다중 망원경 어레이(칠레, 위도 -30.47/경도 -70.78)를 ASCOM Alpaca + PWI4 HTTP API로 제어.

```
applications/  Startup, Shutdown, NightObservation, AppScheduler ...   ← 야간 운영 최상위
    │
action/        level3: Spec/Deep/ColorObservation  (MultiTelescopes 단위)
               level2: SingleObservation, AutoFocus, AutoFlat  (단일 망원경 시퀀스)
               level1: SlewRADec, Exposure, ChangeFilter ...  (단일 디바이스 프리미티브)
               multiaction.py: MultiAction  (망원경별 multiprocessing.Process 병렬화)
    │
devices/       SingleTelescope(unit별 디바이스 묶음), MultiTelescopes(컬렉션),
               TelescopeStatus, pwi4_client, camera/mount/focuser/filterwheel/
               weather/safetymonitor/observer/switch
    │
utils/         databases(타겟 DB), target(SingleTarget/MultiTargets),
               alertmanager(ToO), connector(Slack/Gmail/GSheet/MySQL),
               logger, image(mainImage), nightsession, timeout, datatransfer
    │
configuration/ mainConfig — 거의 모든 클래스의 베이스. ~/TCSpy/configuration/*.config(JSON) 로드
interfaces/    Interface_Runnable / Interface_Abortable (추상 마커)
```

### 핵심 설계 포인트

- **통신 백엔드 2종**: ① ASCOM Alpaca(REST, `alpaca` 패키지, 기본 포트 11111) — camera, filterwheel, switch, weather, safetymonitor. ② PWI4 HTTP(`devices/pwi4_client.py`, 기본 포트 8220, 타임아웃 3초) — mount, focuser, autofocus, fans. 유닛별 `MOUNT_DEVICETYPE`/`FOCUSER_DEVICETYPE`으로 선택(기본 'PWI4').
- **병렬화**: `MultiAction`이 망원경당 `multiprocessing.Process` 1개씩 생성. 액션 인스턴스마다 `Manager().dict()` = `shared_memory`(`succeeded`, `exception`(문자열), `is_running`, `status`)로 프로세스 간 상태 공유.
- **Abort**: `multiprocessing.Event` 하나를 전 계층에 전달. `set()` 시 각 액션 체크포인트에서 `AbortionException` raise. NightObservation은 일반 관측용/ToO용 abort 이벤트를 분리해서 사용.
- **예외 계약**: 액션이 호출자에게 던지는 것은 `ConnectionException`(디바이스 연결 끊김), `AbortionException`(중단), `ActionFailedException`(그 외 실패) 3종뿐. 디바이스별 예외는 액션 내부에서 이 3종으로 변환됨.
- **파일 기반 동기화**: `~/TCSpy/sync/multitelescopes.dict`(unit 활성/busy 상태), 이미지 저장 로그 등을 `portalocker.Lock`으로 프로세스 간 안전하게 공유.
- **상태 어휘**: `'disconnected' | 'idle' | 'busy' | 'parked'(focuser만) | 'safe'/'unsafe'(weather/safetymonitor)`.
- **관측 재개(resume) 메커니즘**: `SingleObservation`의 `observation_status = {filter: {'triggered': n, 'observed': m}}` — 날씨 중단/ToO 선점 후 남은 프레임만 재촬영.

### 하룻밤 운영 타임라인 (AppScheduler `__main__` 기준)

```
sunset_startup(-6°)      Startup (connect→fans→home→slew→cool)
sunset_flat(-8°)         FilterCheck (g/r/i 스카이레벨 점검)
  +15분, +25분           AutofocusInitializer ('specall') ×2
sunset_observation(-15°) NightObservation (메인 관측 루프, ToO 선점 포함)
sunrise_observation      (관측 종료)
sunrise_flat             FlatAcquisition (AutoFlat)
sunrise_shutdown(+10°)   Dark (밤 이미지의 exptime/binning/gain 조합별) → Bias → Shutdown(full)
```

---

## 알려진 버그 / 주의사항 총정리

> **2026-08-06 전체 감사 리포트**: 아래 목록보다 훨씬 상세한 검증·신규 발견(70여 건, 심각도/트리거/결과 포함)은 [CODE_HEALTH_REPORT.md](CODE_HEALTH_REPORT.md) 참조. 일부 항목은 그 감사에서 정정·반박됨 (예: WEATHER_TEMPERATURE는 mainweather가 이중 스왑해 현재 동작은 정상 — 함께 수정 필요).

### 실행이 깨지는 버그
- ~~`NightObservation.abort()` — `a, b = None` unpack TypeError~~ → **2026-08-11 수정됨** (`None, None`으로 변경).
- `action/level1/disconnect.py` — exception 모듈 임포트 누락 → abort 경로에서 NameError.
- `Home.run`/`Park.run` — 실패 핸들러에서 `raise` 누락 → UnboundLocalError.
- `devices/dome/__init__.py`, `devices/rotator/__init__.py` — 존재하지 않는 모듈 import (임포트 시 ImportError).
- `AppScheduler.set_alert_sender` — 미정의 변수 `alert_slack` 참조 가능 (NameError).

### 조용히 잘못 동작하는 버그
- `SingleTelescope.register_logfile()` — None 반환이라 `__init__`에서 `self.log = None`이 됨.
- `TelescopeStatus.mount` PWI4 분기 — 존재하지 않는 `axis2` 참조, 예외가 조용히 삼켜짐.
- Level3 공통 — `'dicconnected'` 오타로 연결 사전 체크 무력화; `autofocus_elapsed_time` 파라미터명 불일치(`autofocus_elapsed_duration`이어야 함 → 기본값 60 사용됨); `all(dict-of-dicts)`는 항상 truthy라 succeeded 판정 무의미.
- `MultiTelescopes.add()` — `_devices_list` 미갱신 → 추가된 unit이 `status`/`filters`에 안 보임.
- `MultiAction.run()` — 시작 시 `abort_action.clear()` 수행 (직전에 걸린 abort 요청이 소멸).
- `AutoFlat` — `sky_level_acceleration` 계산이 같은 변수끼리의 뺄셈이라 항상 0.
- `AutoFocus` — 전체 실패 시 예외 없이 None 반환, `shared_memory['is_running']`이 True로 남음.
- `DB_Dynamic._scorer` — 고정 시각 타겟이 존재할 때 `idx_best` 인덱스 불일치로 엉뚱한 행 반환 가능.
- `AlertMonitor.trigger_alert` — 다중 타겟 알림에서 `['id'][0]`만 검사 (첫 타겟만 관측 여부 확인).
- `Alert.decode_mail` — `is_ToO` 기본값 1(int)이 문자열 'TRUE' 비교에 걸리지 않아, 메일에 명시 안 하면 is_ToO=0이 됨.
- `FilterCheck` — `self.result`에 마지막 필터의 아웃라이어만 저장; `__main__`의 IMAGE_SAVELOG 복원이 True 하드코딩.
- `Startup` FansOn 단계 — 7DT02 존재 시 7DT02/7DT06 하드코딩 제외 + `params[:-1]` 슬라이스.
- `Warm.run` — disconnected 시 raise 대신 return; 시작 시 `is_running=False`로 설정.
- `mainImage.save` — 중복 파일명이 폴더 밖 `IMAGE_PATH/dup_<파일명>`으로 저장됨.
- `WEATHER_TEMPERATURE_UPPER`(-25)/`LOWER`(40) — 값이 서로 뒤바뀐 것으로 보임.
- `MultiTargets` 생성자 — `observer` 파라미터를 받지 않음(**kwargs로 버려짐), 내부에서 항상 새 `mainObserver()` 생성.

### 보안/운영 주의
- MySQL 비밀번호가 `SQLconnector.py`와 `mainconfig.py`에 평문 하드코딩.
- **import 시 즉시 실행되는 파일** (절대 임포트 금지): `devices/power.py`(하드웨어 접속), `utils/check_focus_offset.py`(input 프롬프트), `applications/defocus_test.py`(하드웨어 구동), `applications/fanonofftest.py`(무한 스케줄 루프), `utils/databases/load_7DT_tile.py`(레거시, 임포트 경로도 깨짐). (`utils/ditheringpattern.py`는 2026-08 리팩토링으로 임포트 안전해짐)
- `applications/autofocus_init.py`의 `FILTINFO_FILE = '/home/kds/TCSpy/configuration/filtinfo.dict'` 절대경로 하드코딩.

---

## 파일 인덱스 (무엇을 찾을 때 어디를 볼까)

| 찾는 것 | 파일 |
|---|---|
| 설정 키 정의/기본값 | `configuration/mainconfig.py` |
| 야간 관측 메인 루프, ToO 선점/재개 | `applications/nightobservation.py` |
| 하룻밤 스케줄 타임라인 | `applications/appscheduler.py` (`__main__`) |
| 노출→FITS 저장 흐름 | `action/level1/exposure.py` + `utils/image/mainimage.py` |
| 다필터 관측 시퀀스/재개 | `action/level2/singleobservation.py` |
| 디더링 (spiral, PWI4 offset) | `utils/ditheringpattern.py` + `action/level2/singleobservation.py` + `devices/mount/mainmount_pwi4.py` |
| 오토포커스 로직/히스토리 | `action/level2/autofocus.py` |
| 트와일라잇 플랫 | `action/level2/autoflat.py` |
| 망원경 병렬 실행 | `action/multiaction.py` |
| Spec/Deep/Color 모드 | `action/level3/*.py` |
| 디바이스 상태 문자열 | `devices/telescopestatus.py` |
| PWI4 API | `devices/pwi4_client.py` |
| unit 디바이스 묶음 | `devices/singletelescope.py` |
| 밤 시간 경계 계산 | `utils/nightsession.py` |
| 베스트 타겟 선정/스코어링 | `utils/databases/DB_dynamic.py` (`best_target`/`_scorer`) |
| 서베이 타일 선정 | `utils/databases/DB_survey.py` (`select_best_targets`) |
| 타일 기하/매칭 | `utils/databases/tiles.py` |
| 타겟 관측가능성 | `utils/target/singletarget.py`, `multitargets.py` |
| ToO 알림 수신/처리 | `utils/alertmanager/alertmonitor.py`, `alertbroker.py`, `alert.py` |
| Slack/Gmail/GSheet/MySQL | `utils/connector/*.py` |
| 데이터센터 전송 | `utils/datatransfer.py` |
| 예외 클래스 목록 | `utils/exception/exception.py` |

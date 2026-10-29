# TCSpy 코드 리뷰 리포트

- 작성일: 2026-09-17
- 범위: 저장소 내 `.py` 121개 파일 전체 (약 22,800줄). `__pycache__`, 데이터 파일 제외.
- 방법: 정적 코드 리딩. 실제 장비/DB 실행은 하지 않았으므로 "실행 시 반드시 발생"이 아니라 "코드 경로상 발생 가능"을 기준으로 판정.
- 표기: 각 항목은 **ID / 심각도 / 분류 / 파일 / 위치·의도 / 문제 요소 / 개선 제안** 순서.

## 0. 리포트 포맷에 대한 제안

요청하신 4개 항목(파일 경로, 위치·의도, 문제 요소, 개선 제안)은 그대로 유지하되 다음 3가지를 추가했습니다.

| 추가 필드 | 이유 |
|---|---|
| **ID** (예: A3) | 이슈 트래커·커밋 메시지에서 참조하기 위해 |
| **심각도** (Critical / High / Medium / Low) | 어떤 것부터 고칠지 우선순위를 바로 알 수 있도록 |
| **분류** (Bug / Safety / Concurrency / Security / Design / Hygiene) | 같은 종류의 문제를 한 번에 처리할 수 있도록 |

또한 "파일 순서"가 아니라 "심각도 순서"로 묶었습니다. 파일별로 보고 싶으면 ID 옆의 경로로 grep 하시면 됩니다.

심각도 기준:
- **Critical**: 야간 관측 중단·무한 대기, 장비 상태 오판, 데이터/설정 손실, 자격증명 노출
- **High**: 특정 조건에서 확실히 오동작하거나 성능/자원을 크게 낭비
- **Medium**: 잠재 버그, 잘못된 결과가 조용히 기록됨, 유지보수 위험
- **Low**: 정리, 스타일, 죽은 코드

## 1. 요약

| 심각도 | 건수 |
|---|---|
| Critical | 10 |
| High | 20 |
| Medium | 26 |
| Low | 8 |

가장 먼저 고칠 것 5개:
1. **A1/A3/A4** 예외가 나면 `is_running`이 True로 남아 NightObservation·AppScheduler가 영원히 대기하는 구조. Shutdown까지 못 가는 경로가 있음.
2. **A5** `TelescopeStatus`가 마운트를 항상 `idle`, 끊긴 카메라를 `idle`로 보고. 모든 액션의 "busy/disconnected" 가드가 무력화됨.
3. **A8** 날씨/안전모니터 값이 `None`일 때 안전으로 통과(fail-open).
4. **A9** DB 비밀번호·개인 이메일·서버 정보가 소스와 git 히스토리에 커밋됨.
5. **B1** 액션 인스턴스마다 `multiprocessing.Manager()` 서버 프로세스를 새로 띄움. 16대 관측 시 프레임마다 수십 개 프로세스 생성.

---

## 2. Critical

### A1. 자식 프로세스 비정상 종료가 "관측 성공"으로 기록됨
- **분류**: Bug / Safety
- **파일**: `applications/nightobservation.py`
- **위치·의도**: `execute_observation()` 229~247행. 액션을 `Process`로 실행한 뒤 `action.shared_memory['exception']` 값으로 DB 상태를 `observed/aborted/failed`로 갱신.
- **문제 요소**:
  - 자식이 `ConnectionException`, `KeyError`, `RuntimeError`(singleobservation.py 278행) 등 세 분기 외 예외로 죽으면 `exception`이 `None` 또는 미처리 문자열로 남음.
  - `None`이면 target이 `observed`로 기록되고, `ConnectionException`이면 어느 분기에도 안 걸려 DB는 `scheduled`, 상태파일은 `busy`로 영구 고착.
- **개선 제안**: `process.exitcode != 0`이면 실패로 처리. `exception`에 대한 `else` 분기 추가. 액션 쪽에서는 모든 예외를 `shared_memory['exception']`에 기록하는 공통 `finally` 사용(D7 참고).

### A2. `abort()` 호출 시 항상 TypeError
- **분류**: Bug
- **파일**: `applications/nightobservation.py`
- **위치·의도**: `abort()` 256행. 진행 중 관측을 중단하고 상태를 반환.
- **문제 요소**: `aborted_action, aborted_observation_status = None` → `None`은 언패킹 불가. 수동 중단 기능 자체가 동작하지 않음.
- **개선 제안**: `= None, None`으로 수정. 단위 테스트 추가.

### A3. 자동초점 실패 경로에서 `is_running`이 True로 남아 상위 루프가 무한 대기
- **분류**: Bug / Concurrency
- **파일**: `action/level2/autofocus.py`, `action/level2/autoflat.py`
- **위치·의도**:
  - autofocus.py 281~306행: 자동초점이 끝내 실패하면 원위치로 복귀 후 종료.
  - autoflat.py 341~346행: 모든 필터 완료 후 종료.
- **문제 요소**:
  - autofocus: 예외를 던지지 않고 `run()`이 `None`을 반환. `shared_memory['is_running']`이 True로 남음. 호출자(`SingleObservation`)는 `except ActionFailedException`을 기대하므로 실패를 인지하지 못함.
  - autoflat: 성공 경로에서 `shared_memory['is_running'] = False`를 설정하지 않음.
  - `NightObservation._abort_observation()`은 `while action.shared_memory['is_running']: sleep` 이므로 날씨 악화 시 중단 절차가 영원히 멈춤.
- **개선 제안**: 모든 종료 경로에서 `is_running=False`. 실패 시 `ActionFailedException` raise. `try/finally`로 상태 정리 일원화.

### A4. 애플리케이션 스레드가 예외로 죽으면 스케줄러가 영구 정지 (Shutdown 미실행)
- **분류**: Safety / Concurrency
- **파일**: `applications/appscheduler.py`, `applications/startup.py`, `shutdown.py`, `nightobservation.py`, `biasacquisition.py`, `darkacquisition.py`, `flatacquisition.py`, `autofocus_init.py`
- **위치·의도**: 각 앱은 `run()`에서 `Thread(target=self._process)`를 띄우고, `AppScheduler.run_*()`는 `while action.is_running: sleep(1)`로 완료를 기다림.
- **문제 요소**: `_process()` 안에서 잡히지 않은 예외가 나면 스레드는 죽고 `is_running`은 True 유지 → 스케줄러가 해당 job에서 멈춤 → 이후 예약된 Flat/Dark/Bias/**Shutdown**이 실행되지 않음. 새벽에 망원경이 미파킹·냉각 상태로 방치될 수 있음.
- **개선 제안**: `_process()` 전체를 `try/finally: self.is_running=False`로 감싸고 예외는 로그+`self.exception`에 저장. `run()`이 스레드를 반환하고 스케줄러는 `thread.join(timeout)`으로 대기. Shutdown은 어떤 상황에서도 실행되도록 독립 워치독(별도 프로세스/cron)으로 분리 권장.

### A5. 장비 상태 판정 오류: 마운트는 항상 `idle`, 끊긴 카메라도 `idle`
- **분류**: Bug / Safety
- **파일**: `devices/telescopestatus.py`
- **위치·의도**:
  - `mount` 89행: PWI4 축 enable 여부로 parked 판정 후 slewing/tracking 판정.
  - `camera` 31~57행: `CameraState`를 5초 타임아웃으로 조회.
- **문제 요소**:
  - `mount_status.mount.axis2`는 존재하지 않음(`pwi4_client.py`는 axis0/axis1만 제공). AttributeError가 bare except로 삼켜져 `is_slewing` 검사 전에 빠져나감 → 슬루 중에도 `idle`. Slew/Park/Home 액션의 "mount is busy" 가드가 절대 동작하지 않음.
  - `call_with_timeout`이 실패하면 문자열 `'disconnected'`를 반환하는데, 이어지는 `state.name` 접근이 AttributeError → except에서 `status='idle'`로 설정. 끊긴 카메라가 `idle`로 보고되어 Exposure가 진행됨.
  - `filterwheel`은 연결 확인 없이 항상 `idle`.
- **개선 제안**: `axis1`로 수정. 예외 시 `'disconnected'` 반환. 필터휠은 `device.Connected` 확인. 상태 문자열을 Enum으로 정의해 오타 방지.

### A6. 예외 객체를 `raise` 대신 `return`
- **분류**: Bug
- **파일/위치**:
  - `devices/mount/mainmount_pwi4.py` 293행 `park()`: 중단 시 `return AbortionException(...)` → 중단이 "성공"으로 처리되고 `finally`의 재-raise도 안 됨.
  - `devices/focuser/mainfocuser_alpaca.py` 206행 `disconnect()`: `return ConnectionException(...)`.
  - `action/level1/warm.py` 89행: `return ConnectionException(...)`.
  - `devices/singletelescope.py` 184, 192행: `return TelTypeError(...)`/`FocuserTypeError(...)` → mount/focuser 속성에 예외 객체가 들어가고 나중에 의미 불명 AttributeError.
- **개선 제안**: 모두 `raise`. flake8/ruff의 `B` 계열 규칙(`useless-expression`)으로 자동 검출 가능.

### A7. Park/Home 액션: 예외를 생성만 하고 raise 안 함, 변수 미정의
- **분류**: Bug
- **파일**: `action/level1/park.py` 99~102행, `action/level1/home.py` 99~102행
- **위치·의도**: 마운트 파킹/호밍 실패 시 `ActionFailedException`으로 변환.
- **문제 요소**:
  - `ActionFailedException(...)` 앞에 `raise`가 없음 → 그대로 진행 → 110행 `if result_park:`에서 `UnboundLocalError`.
  - home.py는 `ParkingFailedException`을 잡지만 `find_home()`은 `FindingHomeFailedException`을 던짐 → 잡히지 않음.
  - Alpaca 마운트의 `find_home()`은 `abort_action` 인자를 받지 않음 → TypeError.
- **개선 제안**: `raise` 추가, 올바른 예외 타입 catch, `shared_memory['exception']` 설정.

### A8. 안전 판정 fail-open (`None`을 안전으로 통과)
- **분류**: Safety
- **파일**: `action/level2/autofocus.py` 98행, `action/level2/autoflat.py` 52행
- **위치·의도**: 날씨/안전모니터가 unsafe면 액션을 거부.
- **문제 요소**: `get_status()['is_safe'] == False` 비교. 장치 미연결·파일 stale 시 `is_safe`는 `None`이라 조건이 False → 안전한 것으로 간주하고 돔 열림 여부와 무관하게 슬루/노출 진행. (`nightobservation.py`의 `_is_*_safe`는 `== True`라 fail-closed로 올바름. 두 곳이 다름.)
- **개선 제안**: `is not True`로 통일. `is_safe` 판정 함수를 한 곳(`mainWeather.is_safe()`)으로 모으고 `None`은 unsafe로 정의.

### A9. 자격증명·개인정보가 소스와 git 히스토리에 포함
- **분류**: Security
- **파일/위치**:
  - `configuration/mainconfig.py` 219행: DB 비밀번호 평문(주석에 두 번째 비밀번호까지). 174~176행 전송 서버 IP/계정. 241~252행 개인 이메일 목록.
  - `utils/connector/SQLconnector.py` 11~12행: 기본 인자에 계정/비밀번호.
  - `utils/databases/load_7DT_tile.py` 7행: 비밀번호.
  - `.vscode/sftp.json`: 서버 호스트·계정, `uploadOnSave: true`.
  - `utils/alert_history/gmail/*/attachments/*.json`: 외부 사용자의 ToO 요청(요청자 이름·좌표 등) 7건이 커밋됨.
  - `utils/alertmanager/alertbroker.py` 471, 489, 524, 544~545행: 메일 본문에 개인 이메일 하드코딩.
- **문제 요소**: 저장소가 공유되면 DB 접근 가능. 비밀번호는 이미 히스토리에 있으므로 파일에서 지워도 남음.
- **개선 제안**: 비밀번호 즉시 교체. `credential/` 디렉터리(이미 gmail/slack/googlesheet는 이 방식) 또는 환경변수로 이동. `git filter-repo`로 히스토리 정리. `.gitignore`에 `credential/`, `*.json`(alert_history), `.vscode/` 추가. 개인 이메일은 config로.

### A10. `mainconfig.py` 직접 실행 시 16대 전체 설정 파일이 기본값으로 덮어써짐
- **분류**: Safety / Design
- **파일**: `configuration/mainconfig.py` 376~405행, `_initialize_config()` 303~334행
- **위치·의도**: 최초 설치 시 유닛별·전역 config JSON 생성.
- **문제 요소**:
  - `if __name__ == '__main__':` 블록 두 개가 무조건 실행되어 1~16번 유닛 전부 `_initialize_config()` 호출. 실서비스에서 손으로 수정한 값(IP, 포트, AUTOFLAT 파라미터, 필터 순서 등)이 코드 안 기본값으로 원복됨.
  - `_initialize_config()`는 전역 config(observer, db, autoflat …)도 매 호출마다 다시 쓰므로 16회 덮어씀.
  - 두 번째 블록은 unit 21(127.0.0.1)용인데 전역 파일도 다시 덮어씀.
- **개선 제안**: `argparse`로 `--unit`, `--force` 옵션화. 기존 파일이 있으면 기본적으로 건너뛰고 `--force`일 때만 덮어쓰기. 전역 config는 별도 함수로 분리하여 한 번만 생성.

---

## 3. High

### B1. 액션 인스턴스마다 `Manager()` 서버 프로세스 생성
- **분류**: Design / Performance
- **파일**: `action/multiaction.py` 61행 및 `action/level1/*.py`, `level2/*.py`, `level3/*.py` 모든 `__init__`
- **위치·의도**: 자식 프로세스와 결과(`succeeded`, `exception`, `status`)를 공유하기 위해 `Manager().dict()` 사용.
- **문제 요소**: `Manager()`는 호출마다 별도 서버 프로세스를 fork함. `MultiAction(16대, Exposure)` 한 번에 Manager 17개 + 워커 16개. `SingleObservation`은 내부에서 `Exposure`, `ChangeFilter`, `AutoFocus`를 생성하며 각각 또 Manager를 띄움. 프레임마다 반복되므로 프로세스 생성 비용·fd 소모가 크고, Manager는 `shutdown()`되지 않아 GC에 의존. 노출 사이 dead time의 주요 원인 후보.
- **개선 제안**: 애플리케이션 단위로 하나의 Manager를 만들어 주입하거나, `Process` + `Pipe/Queue`로 결과만 회수. 더 단순하게는 `concurrent.futures.ProcessPoolExecutor`로 `run()`을 제출하고 반환값/예외를 그대로 받는 구조.

### B2. 같은 target이 두 망원경에 중복 배정되는 경쟁 조건
- **분류**: Concurrency
- **파일**: `applications/nightobservation.py` 198~224행
- **위치·의도**: `dispatch_observation()`은 스레드를 띄우고 즉시 반환. 스레드(`execute_observation`)가 DB에 `scheduled`를 기록.
- **문제 요소**: 메인 루프는 0.5초 후 다시 `best_target()`을 조회. DB 갱신이 그보다 늦으면 같은 target을 다시 뽑아 다른 유닛에 배정. SEARCH 모드는 망원경은 `popitem`으로 즉시 빼지만 target 상태는 비동기라 target 중복은 막지 못함.
- **개선 제안**: `dispatch_observation()` 안에서 동기적으로 DB `scheduled` 갱신(또는 메모리 `dispatched_ids` 집합을 `best_target`에 exclude 인자로 전달) 후 스레드 시작.

### B3. ToO 종료 후 일반 관측 재개가 절대 일어나지 않음
- **분류**: Bug
- **파일**: `applications/nightobservation.py` 373~377행
- **위치·의도**: ToO로 중단된 일반 관측을 망원경이 비어 있으면 재개.
- **문제 요소**: `action['telescope']`가 `SingleTelescope`면 `.devices.keys()`는 `camera, mount, …`(장치명)이라 `tel_queue.keys()`(망원경명)의 부분집합이 될 수 없음 → 조건 항상 False. `MultiTelescopes`일 때만 우연히 맞음.
- **개선 제안**: `isinstance`로 분기해 망원경 이름 집합을 구성. `_put_telescope/_pop_telescope`처럼 헬퍼로 통일.

### B4. 관측 모드별 자원 조건 미충족 시 스케줄러가 같은 target에 고착(starvation)
- **분류**: Design
- **파일**: `applications/nightobservation.py` 157~196행
- **위치·의도**: COLOR/SPEC은 전체 유닛 idle, DEEP은 N대 idle일 때만 dispatch.
- **문제 요소**: 조건 미충족이면 아무 것도 하지 않고 다음 루프에서 다시 같은 최고점 target을 뽑음. 한 대가 관측 중이면 SPEC target이 계속 최고점이라 나머지 유닛이 모두 놀게 됨. 유닛이 하나라도 제외(`remove`)되면 SPEC/COLOR는 영구 불가.
- **개선 제안**: `best_target()`에 "현재 가용 유닛 수"를 전달해 조건 맞는 target만 점수화하거나, 실패 target을 짧게(예: 5분) skip 목록에 넣기.

### B5. Level3 관측 결과 판정·연결 확인·파라미터 전달 오류
- **분류**: Bug
- **파일**: `action/level3/specobservation.py`, `colorobservation.py`, `deepobservation.py`
- **위치·의도**: 다중 망원경 관측 실행 후 성공 여부 판정, 사전 연결 확인, `SingleObservation`에 파라미터 전달.
- **문제 요소**:
  - 265/262/268행 `all(self.shared_memory['status'].values())`: 값이 dict proxy라 항상 truthy → `succeeded`가 항상 True.
  - `'dicconnected'` 오타 12곳 → 연결 체크가 절대 참이 되지 않음.
  - 237/234/240행 `autofocus_elapsed_time=`으로 넘기지만 `SingleObservation.run()`의 인자명은 `autofocus_elapsed_duration` → `**kwargs`로 조용히 흡수되어 항상 기본값 60분 사용.
  - `deepobservation.py` `_format_params` 미사용, `ntelescope` 인자 무시.
- **개선 제안**: `all(v['succeeded'] for v in status.values())`. 상태 문자열 상수화. 파라미터 이름 통일 후 `**kwargs` 제거(오타 시 TypeError로 드러나게).

### B6. Connect/Disconnect 액션이 결과와 무관하게 성공 보고
- **분류**: Bug
- **파일**: `action/level1/connect.py` 72~75, 98행; `action/level1/disconnect.py` 72~75, 97행
- **위치·의도**: 모든 장치 connect 후 상태 확인, 실패 장치 로그.
- **문제 요소**:
  - `device.connect()` 예외를 bare except로 무시하고 마지막에 `succeeded=True` 고정. `Startup`의 "연결 실패 유닛 제외" 로직이 동작하지 않음.
  - `self.telescope.devices`에 공유 장치(weather, safetymonitor)가 포함되어 16개 프로세스가 동시에 같은 Alpaca 장치에 connect/disconnect. Disconnect 시 한 유닛이 전체 날씨 장치 연결을 끊을 수 있음.
  - disconnect.py 59행 `is_running=False`(True여야 함).
- **개선 제안**: 사후 상태에 `disconnected`가 있으면 `succeeded=False`. 공유 장치는 유닛 액션 대상에서 제외.

### B7. Startup 팬 제어에 유닛명 하드코딩 + 잘못된 슬라이싱
- **분류**: Bug / Design
- **파일**: `applications/startup.py` 133~145행
- **위치·의도**: 7DT02/06/13은 팬을 켜지 않음.
- **문제 요소**: `params_fanson[:-1]`은 제외 유닛 수와 무관하게 1개만 자름. 제외 유닛이 없으면 `zip`이 마지막 망원경을 조용히 건너뜀. 유닛명 하드코딩은 config 대상.
- **개선 제안**: `params = [dict() for _ in multitelescopes_fanon]`. 제외 목록은 `STARTUP_FAN_EXCLUDE` config 키로.

### B8. 필터휠 `get_status()`가 미연결 시 `None` 반환, 재시도 로직 사문화
- **분류**: Bug
- **파일**: `devices/filterwheel/mainfilterwheel.py` 107~158, 350~353행
- **위치·의도**: 상태 dict 반환, 타임아웃 시 3회 재시도, 현재 필터명 조회.
- **문제 요소**:
  - 148행 `return status`가 `if self.device.Connected:` 블록 안에 들여쓰기 → 미연결 시 `None` 반환 → 호출자 `status['filter_']`에서 TypeError.
  - `except TimeoutException`을 잡지만 `Timeout` 데코레이터는 일반 `Exception`을 던짐(저장소 어디에서도 `TimeoutException`을 raise하지 않음) → 재시도 없이 즉시 전파. 3회 모두 실패하면 `status` 미정의.
  - `_get_current_filtinfo()`: 이동 중 ASCOM `Position == -1`이면 `filtnames[-1]`(마지막 필터)을 반환 → 헤더에 잘못된 FILTER 기록 가능.
  - `move()` 222행 `> len` → `>=` 여야 함. `move()`는 `abort_action`을 받지 않아 중단 불가.
- **개선 제안**: 들여쓰기 수정, `Timeout`이 `TimeoutException`을 던지게 변경(B9), Position -1 처리.

### B9. `Timeout` 데코레이터의 반쪽 타임아웃
- **분류**: Design / Concurrency
- **파일**: `utils/timeout.py` 31~61행
- **위치·의도**: 장치 호출이 멈출 때 상위로 타임아웃을 알림.
- **문제 요소**:
  - 스레드 기반이라 타임아웃 후에도 워커 스레드는 계속 실행됨(`connect()`의 `while not Connected` 루프가 백그라운드에서 영원히 돔). 데몬 스레드가 누적.
  - 일반 `Exception`을 던져 호출자가 타임아웃과 다른 오류를 구분 못함. `TimeoutException`이 정의만 되어 있음.
  - `res[0]`에 예외를 저장하고 `isinstance(ret, BaseException)`로 판별하므로 함수가 정상적으로 예외 객체를 반환하는 경우(A6 패턴)와 충돌.
- **개선 제안**: `TimeoutException` raise. Alpaca 클라이언트 자체 HTTP timeout(`alpaca` 패키지는 requests 기반, `Device.timeout` 설정 가능)과 PWI4 `timeout_seconds`를 활용해 블로킹 자체를 줄이고, 루프에는 경과시간 상한을 두는 협조적 타임아웃으로 전환.

### B10. 카메라 상태 조회마다 `ThreadPool` 생성 후 미종료
- **분류**: Bug / Performance
- **파일**: `devices/telescopestatus.py` 31~38행
- **위치·의도**: `CameraState` 조회에 5초 타임아웃 적용.
- **문제 요소**: `ThreadPool(processes=1)`을 매 호출 생성하고 `close()/join()` 없음. `MultiTelescopes.status`, `_put_telescope`, 각 액션 시작 시 호출되므로 야간 수천 회 → 스레드/fd 누수.
- **개선 제안**: `with ThreadPool(1) as pool:` 또는 모듈 수준 `ThreadPoolExecutor` 하나를 재사용.

### B11. 카메라 모듈의 `None` 포매팅·dtype 미정의
- **분류**: Bug
- **파일**: `devices/camera/maincamera.py`
- **위치·의도**:
  - 431, 508행: 냉각/가열 진행 로그 `'%.1f [Power: %d]' % (temp, cooler_power)`.
  - 278~285행: `ImageArrayElementType`에 따라 numpy dtype 결정.
- **문제 요소**:
  - `CanGetCoolerPower`가 False면 `cooler_power=None` → `%d` TypeError → 냉각이 예외로 중단.
  - ElementType이 Int32/Double 외(Int16 등)이면 `img_dtype` 미정의 → UnboundLocalError. `status['maxADU']`가 None이면 비교에서 TypeError.
  - 591~596행: `StartExposure` 직후 `ImageReady`를 sleep 없이 확인. 짧은 노출/바이어스는 이미 ready일 수 있어 불필요한 abort + 전체 이미지 다운로드("flush") 후 재노출.
- **개선 제안**: `cooler_power`가 None이면 문자열 분기. dtype 기본값 지정. flush 로직은 `StartExposure` 이전에 `ImageReady`를 확인하도록 순서 변경.

### B12. PWI4 `find_home()` 완료 판정이 "0.5초간 위치 불변"
- **분류**: Bug / Safety
- **파일**: `devices/mount/mainmount_pwi4.py` 360~371행
- **위치·의도**: 호밍 중 alt/az 변화량이 0.1도 미만이면 완료로 간주.
- **문제 요소**: 명령 직후 마운트가 아직 출발하지 않았으면 즉시 "완료". 반대로 축이 느리게 움직이는 구간에서도 조기 완료. 이후 슬루가 호밍과 겹칠 수 있음.
- **개선 제안**: `is_slewing`/축 상태 플래그 또는 PWI4가 제공하는 상태를 사용. "움직임 시작 대기(타임아웃 포함) → 정지 대기" 두 단계로.

### B13. Alpaca 마운트/포커서가 PWI4 구현과 인터페이스 불일치
- **분류**: Design / Bug
- **파일**: `devices/mount/mainmount_alpaca.py`, `devices/focuser/mainfocuser_alpaca.py`
- **위치·의도**: 장치 타입별 구현을 `SingleTelescope`가 선택.
- **문제 요소**:
  - `is_idle`, `device_lock`, `wait_idle()`이 없음. 액션 17곳에서 `mount.wait_idle()`/`focuser.wait_idle()` 호출 → Alpaca 구성에서 AttributeError.
  - `find_home()` 시그니처 불일치, `autofocus_start()`가 2-튜플(PWI4는 3-튜플) 반환 → 언패킹 오류.
  - `mainfocuser_alpaca.move()` 최소값 1000 하드코딩(config `FOCUSER_MINSTEP` 무시), 허용오차 10스텝 하드코딩·무한 루프 가능.
  - `mainmount_alpaca.park()`는 실제 `Park()`를 호출하지 않고 슬루만 함 → `AtPark` 절대 True 안 됨.
  - `mainmount_pwi4`에는 `abort()`가 없고 Alpaca에는 있음.
- **개선 제안**: `abc.ABC` 기반 `BaseMount`, `BaseFocuser`를 정의하고 두 구현이 상속. 공통 락/idle 로직은 base에 두기.

### B14. 날씨 온도 임계값이 두 번 뒤집혀 우연히 동작
- **분류**: Bug
- **파일**: `devices/weather/mainweather.py` 196~204행, `configuration/mainconfig.py` 196~197행
- **위치·의도**: config의 온도 상/하한을 constraints로 로드.
- **문제 요소**: config는 `TEMPERATURE_UPPER=-25, LOWER=40`(뒤바뀜), 로더는 `LOWER ← UPPER`, `UPPER ← LOWER`(또 뒤바뀜). 현재는 맞지만 한쪽만 고치면 모든 관측이 unsafe 판정.
- **추가 문제**: `get_status()`(같은 파일 54~88행)는 파일이 5분 이상 stale이면 클라이언트(각 유닛 프로세스)가 직접 장치에 접근해 상태 파일을 덮어씀. 클라이언트 프로세스에서는 `device.Connected`가 False라 `is_connected: False, is_safe: None`인 파일이 기록되어 갱신기(updater)의 정상 데이터를 덮어쓸 수 있음.
- **개선 제안**: 양쪽 모두 바로잡기. 클라이언트는 읽기만 하고 stale이면 `None` 반환(=unsafe). 같은 구조인 `mainsafetymonitor.py`도 동일.

### B15. `SingleTelescope.log`가 생성 직후 `None`
- **분류**: Bug
- **파일**: `devices/singletelescope.py` 73, 154~155행
- **위치·의도**: 유닛별 로거를 `self.log`에 보관.
- **문제 요소**: `register_logfile()`이 내부에서 `self.log`를 설정하고 `None`을 반환하는데, 73행에서 `self.log = self.register_logfile()`로 다시 `None` 대입. 액션들이 매번 `telescope.register_logfile()`을 먼저 호출하는 이유가 이것. 직접 `telescope.log.info()`를 쓰는 코드는 AttributeError.
- **개선 제안**: `register_logfile()`이 로거를 반환하도록 수정. 액션 내 반복 호출 제거.

### B16. `MultiTelescopes.add()/remove()`가 내부 리스트를 갱신하지 않음
- **분류**: Bug
- **파일**: `devices/multitelescopes.py` 88~115, 128, 140, 194행
- **위치·의도**: 망원경 추가/제거.
- **문제 요소**: `devices` dict만 갱신하고 `_devices_list`는 그대로 → `.status`, `.filters`, `_dict_logs()`는 제거된 유닛을 계속 폴링. `Startup/Shutdown`은 실패 유닛을 `remove()`하는데, 같은 객체를 `NightObservation`이 공유하므로 야간 중 유닛 집합이 조용히 바뀜. `_load_from_config()`와 `__init__`이 `_register()`를 두 번 호출.
- **개선 제안**: 단일 소스(`devices` dict)만 유지하고 나머지는 파생. 관측 대상 집합 변경은 명시적 이벤트/로그로.

### B17. AutoFlat 노출시간 예측 로직 오류
- **분류**: Bug
- **파일**: `action/level2/autoflat.py` 229~232, 302~303행
- **위치·의도**: 하늘 밝기 변화율(가속)로 다음 노출시간 예측.
- **문제 요소**:
  - 230행 `np.abs(sky_level_per_second_this - sky_level_per_second_this)` → 항상 0. 이전 값을 저장하지 않아 가속 보정이 죽어 있음.
  - `sky_level`이 0 또는 음수(바이어스 추정 오차)면 302행에서 ZeroDivisionError 또는 `np.abs`로 부호가 가려진 잘못된 노출시간.
  - 알고리즘이 "밝아지는 하늘"(새벽)만 가정. 저녁 flat에 쓰면 "Sky is too bright"로 즉시 실패.
- **개선 제안**: `prev` 변수 도입. `sky_level <= 0` 가드. 저녁/새벽 모드 인자.

### B18. `SingleObservation` 초기 상태·예외 변환 문제
- **분류**: Bug
- **파일**: `action/level2/singleobservation.py` 56, 172~199, 277~278행
- **위치·의도**: 초기 shared_memory 설정, 장치 상태 조회, 슬루 예외 처리.
- **문제 요소**:
  - 56행 `is_running=True`로 초기화 → `run()` 전에 `abort()`가 호출되면 무한 대기.
  - 172~191행 try에서 실패하면 `status_mount` 등이 미정의 상태로 193행 이후 NameError.
  - 277~278행 `except Exception as e: raise RuntimeError(...)` → `shared_memory['exception']` 미설정 + 원인 스택 소실 → A1로 이어짐.
- **개선 제안**: 초기값 False. `raise ... from e`. 모든 예외를 공통 finally에서 기록.

### B19. AppScheduler의 NameError와 효과 없는 config 토글
- **분류**: Bug
- **파일**: `applications/appscheduler.py` 128, 162~175행; `applications/biasacquisition.py` 129행
- **위치·의도**: Slack 공지, filtercheck 이미지 로그 비활성화.
- **문제 요소**:
  - 128행 `alert_slack` 미정의 변수 → 라이브러리로 `set_alert_sender(post_tonight_info=True)` 호출 시 NameError(스크립트 실행 시엔 전역 변수로 우연히 동작).
  - `mainConfig(...).update_config('IMAGE_SAVELOG', False)`는 디스크 파일만 바꾸고 이미 로드된 `telescope.config`에는 영향 없음 → filtercheck 이미지도 로그에 기록됨. (`__main__`에서는 `MultiTelescopes()`를 다시 만들어 우회.)
  - biasacquisition.py 129행 `update_config('IMAGE_SAVELOG', original_config)` → 리스트를 통째로 저장.
- **개선 제안**: 런타임 설정 변경은 객체 속성으로(`telescope.config['IMAGE_SAVELOG']=False`) 하고 파일은 건드리지 않기. 변수명 수정.

### B20. 로거: 날짜 고정 파일 핸들러 + 로거마다 `mainObserver` 생성
- **분류**: Design / Performance
- **파일**: `utils/logger/mainlogger.py` 37~41, 76~94행
- **위치·의도**: 유닛별 로거 생성, 날짜별 로그 파일.
- **문제 요소**:
  - 로거는 이름별로 캐시되고 파일 핸들러 경로는 생성 시점 날짜로 고정 → 장기 실행 프로세스(appscheduler, alertmonitor, 갱신기)는 다음 날에도 전날 파일에 기록.
  - 생성마다 `mainObserver()`(astroplan Observer + `moon_illumination` 계산)를 만들지만 사용하지 않음. 유닛당 장치 4개 + SingleTelescope + 액션마다 호출 → 시작 시간 수십 초 증가.
  - `self.path = None`이 `mainConfig.path`(TCSpy 루트 경로)를 덮어씀.
- **개선 제안**: `TimedRotatingFileHandler` 또는 로그 시점 날짜를 계산하는 커스텀 핸들러. observer 제거. 속성명 변경.

---

## 4. Medium

### C1. 함수 기본 인자로 `Time.now()` 사용 (임포트 시점 고정)
- **분류**: Bug
- **파일**: `utils/nightsession.py` 10, 18행; `utils/databases/DB_dynamic.py` 71, 185, 268, 297행; `mainDB.py` 40행; `DB_survey.py` 93, 157행; `DB_program.py` 93, 138행
- **문제 요소**: 기본값이 모듈 임포트 시각으로 고정됨. 장기 실행 시 `NightSession()`이 하루 전 밤을 계산할 수 있음.
- **개선 제안**: `utctime: Time = None` 후 함수 내 `Time.now()`.

### C2. 임포트만으로 플롯을 띄우는 모듈
- **분류**: Hygiene
- **파일**: `utils/ditheringpattern.py` 64~94행
- **문제 요소**: 모듈 최상위에서 패턴 생성 + `plt.show()`. 현재는 어디서도 import되지 않지만 `tcspy.utils` 하위에 있어 실수로 import되면 headless 서버에서 예외/블로킹.
- **개선 제안**: `if __name__ == '__main__':` 아래로 이동. 나선 방향/중복 처리 로직도 재검토(`if next_position in visited: 위로 이동`은 임의 규칙).

### C3. 패키지 내부의 실행형 스크립트(하드웨어 명령 포함)
- **분류**: Safety / Hygiene
- **파일**: `action/level1/test.py`, `action/test.py`, `applications/defocus_test.py`, `applications/fanonofftest.py`, `applications/get_target_telescope.py`, `applications/missingobservation.py`, `devices/power.py`, `utils/check_focus_offset.py`, `utils/databases/load_7DT_tile.py`
- **문제 요소**: 모듈 최상위에서 `SingleTelescope(21)` 생성, 슬루/포커스 이동, 스케줄 루프 실행. `import tcspy.applications.defocus_test` 한 줄로 10대 망원경이 움직임. `/home/kds/...` 절대경로 다수. `load_7DT_tile.py`는 존재하지 않는 메서드(`initialize_tbl`, `insert_data`)를 호출.
- **개선 제안**: `scripts/` 또는 `examples/`로 이동하고 패키지에서 제외. 필요한 것은 `__main__` 가드.

### C4. 존재하지 않는 모듈을 import하는 `__init__`
- **분류**: Bug
- **파일**: `devices/dome/__init__.py`, `devices/rotator/__init__.py`
- **문제 요소**: `maindome.py`, `mainrotator.py`가 없음 → 해당 서브패키지 import 시 ImportError. `TelescopeStatus.dome`은 항상 `'disconnected'`.
- **개선 제안**: 삭제하거나 스텁 구현 추가.

### C5. 예외 체계 이원화 및 내장 예외 혼용
- **분류**: Design
- **파일**: `utils/exception/exception.py`, `utils/error/error.py`, `devices/camera/maincamera.py` 348, 368행
- **문제 요소**: 두 모듈에 예외가 분산. 카메라만 내장 `ConnectionError`를 던지고 나머지는 `ConnectionException`. `Connect` 액션의 bare except가 가리지만 다른 호출자는 못 잡음.
- **개선 제안**: 단일 모듈, 공통 베이스 `TCSpyError` 정의.

### C6. Exposure 액션: 프레임마다 전체 장치 상태 폴링, 저장 오류 은폐
- **분류**: Bug / Performance
- **파일**: `action/level1/exposure.py` 258~287행
- **문제 요소**: `self.telescope.status`는 카메라·마운트·포커서·필터휠·날씨·안전모니터 6개를 순차 조회(HTTP 4회 + 파일 glob 2회). 프레임 간 dead time 증가. 저장 블록의 bare except가 실제 원인(예: `autofocus_dict[filter_]` KeyError)을 "mainImage save failure"로 뭉뚱그림.
- **개선 제안**: 노출 시작 전 마운트/필터 상태를 한 번만 읽어 헤더에 사용, 날씨는 캐시. `log.exception()`으로 스택 기록.

### C7. 이미지 저장 경로/헤더 세부 문제
- **분류**: Bug
- **파일**: `utils/image/mainimage.py` 142~158, 286행
- **문제 요소**: 파일명 중복 시 `IMAGE_PATH` 루트에 `dup_` 접두로 저장(야간 폴더 밖, `.head` 미생성). `FOCALRAT` 주석 단위 오류. `IS_ToO` 헤더가 `'True'/'False'` 문자열.
- **개선 제안**: 중복 파일은 같은 폴더에 `_dupN` 접미. 헤더 bool은 FITS bool로.

### C8. SQL 문자열 보간 및 커넥션 풀 남용
- **분류**: Security / Design
- **파일**: `utils/connector/SQLconnector.py` 40~43, 101~105, 150, 171행
- **문제 요소**: `update_row`(단일 값), `remove_rows`, `get_data(where_value)`가 값을 f-string으로 SQL에 삽입 → 따옴표 포함 objname(예: `O'Neil`)에서 구문 오류, 인젝션 위험. `disconnect()`가 `pool=None`으로 만들어 이후 호출 AttributeError. `DB()`는 Dynamic/RIS/IMS 각각 풀 16개 생성(=48 커넥션).
- **개선 제안**: 전부 파라미터 바인딩. 프로세스당 풀 하나 공유.

### C9. Dynamic DB 스케줄러 루프 비용 및 제약 미적용
- **분류**: Bug / Performance
- **파일**: `utils/databases/DB_dynamic.py` 106~227, 553~557, 606, 701~707행
- **문제 요소**:
  - `initialize()`+`best_target()`가 매 루프(≈1초)마다 전체 테이블을 3회 SELECT.
  - `constraint_set`(set time/일출 전 완료), `constraint_night` 계산 후 주석 처리로 미적용 → 일출 직전에 긴 관측이 배정될 수 있음.
  - 606행 `np.clip(0, 1, x)` 인자 순서 오류(현재는 `min(1, x)`로 우연히 동작).
  - `_get_target_observable()`은 미정의 변수 `obs_tbl` 참조(죽은 코드).
- **개선 제안**: 변경 시각 컬럼 기준 증분 조회, 제약 적용 여부를 config로 명시, `np.clip(x, 0, 1)`.

### C10. `DB_Survey.select_best_targets()` 결과 조립 로직 불명확
- **분류**: Bug
- **파일**: `utils/databases/DB_survey.py` 246~253행
- **문제 요소**: 첫 그룹에서 `size`를 채우면 `best_targets=…`로 덮고 다음 반복에서 이전 `best_target_group`을 다시 vstack → 중복/누락 가능. `best_target_group` 미정의 경로 존재.
- **개선 제안**: 그룹 루프 밖에서 한 번에 조립, `size` 도달 시 break.

### C11. AlertMonitor 다중 target 판정·미정의 변수
- **분류**: Bug / Security
- **파일**: `utils/alertmanager/alertmonitor.py` 143, 168, 198, 258, 278행
- **문제 요소**: `alert_observable_targets['id'][0]`로 첫 target만 확인. `send_slack=False`면 `slack_message_ts` 미정의로 종료 시 NameError. `len(...) < 0`은 항상 False. 알림당 최대 48시간 대기 스레드가 무제한 생성. 발신자 이메일 문자열만으로 권한 판정(스푸핑 가능).
- **개선 제안**: `np.isin(..., ids)` 전체 배열. 변수 초기화. 인증은 DKIM/SPF 통과 여부나 서명 토큰으로.

### C12. AlertBroker의 광범위 `except: raise RuntimeError`
- **분류**: Design
- **파일**: `utils/alertmanager/alertbroker.py` 214~215, 246~247, 296~299, 450, 503, 559, 689, 776, 832, 853행
- **문제 요소**: 원인 예외가 사라져 운영 중 디버깅 불가. `read_mail`은 메일별 오류를 완전히 무시.
- **개선 제안**: `raise ... from e`, 로거에 `exception()` 기록.

### C13. GmailConnector 미정의 메서드/속성
- **분류**: Bug
- **파일**: `utils/connector/gmailconnector.py` 39, 296행
- **문제 요소**: `delete_mail()`이 없는 `ensure_logged_in()` 호출, `__repr__`이 없는 `self.logged_in` 참조. `datetime.utcnow()` deprecated.
- **개선 제안**: `ensure_logged_in_imap()`으로 수정, 속성 정리.

### C14. SlackConnector 메시지 검색 범위
- **분류**: Bug
- **파일**: `utils/connector/slackconnector.py` 13, 60행
- **문제 요소**: `conversations_history` 기본 100건만 조회 → 채널이 활발하면 당일 스레드를 못 찾아 알림이 새 메시지로 흩어짐. 토큰 파일 `read()` 후 `strip()` 없음.
- **개선 제안**: `oldest` 파라미터로 당일 범위 지정, `strip()`.

### C15. DataTransfer: shell 문자열 조립과 스케줄 판정
- **분류**: Security / Bug
- **파일**: `utils/datatransfer.py` 44, 108~147, 129~130, 404, 936~1701행
- **문제 요소**:
  - `subprocess.Popen(shell=True)`에 경로/glob/원격 경로를 f-string으로 삽입 → 공백·특수문자 경로에서 오동작, 인젝션 가능.
  - `start_monitoring`은 `hour==12 and minute==0`을 60초 sleep 루프로 확인 → 드리프트로 건너뛰거나 두 번 실행 가능(주석은 8AM, 코드는 12시).
  - `gridFTP_transfer`는 try 없이 `RuntimeError` → `is_running` True 고착. 로그 경로에 `Time.now().isot`(콜론 포함) 사용.
  - 936행 이후 약 770줄이 동일 클래스의 주석 사본.
- **개선 제안**: `subprocess.run([...], shell=False)` 리스트 인자. 스케줄은 `schedule` 라이브러리 또는 "마지막 실행 날짜" 기록. 주석 사본 삭제.

### C16. `SingleTarget` 생성 비용과 이름 정제 범위
- **분류**: Performance
- **파일**: `utils/target/singletarget.py` 139~142, 148~153행
- **문제 요소**: 생성마다 `mainConfig()`(config 디렉터리 glob + JSON 다수 로드)와 제약 객체 생성. 노출마다·DB 행마다 생성되어 IO 부담. 이름 정제가 공백/`/`/`_`만 처리 → `:` 등은 파일명에 그대로.
- **개선 제안**: config를 인자로 주입하거나 모듈 캐시. 파일명용 sanitize 함수를 `mainImage`에서 일괄 적용.

### C17. PWI4 포커서 자동초점 중 락 해제/재획득
- **분류**: Concurrency
- **파일**: `devices/focuser/mainfocuser_pwi4.py` 130~131, 362~368, 378~380, 385행
- **문제 요소**: `autofocus_start()` 내부에서 `device_lock`을 풀고 `move()`를 호출(그 안에서 `is_idle.set()`이 호출되어 자동초점 중 idle로 보임). 362행 `while status['is_moving']` 루프에 sleep 없음. `get_status()`가 `PWI_status`를 두 번 호출(HTTP 2회, 마운트도 동일). `print(exception_raised)` 디버그 출력.
- **개선 제안**: 내부 이동은 락을 잡지 않는 `_move_nolock()`으로 분리. 상태 1회 조회 후 재사용.

### C18. 날씨/안전모니터 상태 파일 조회 비용
- **분류**: Performance
- **파일**: `devices/weather/mainweather.py` 63~86행, `devices/safetymonitor/mainsafetymonitor.py` 61~86행
- **문제 요소**: 호출마다 당일 디렉터리(분당 1파일, 하루 1440개) glob + 파일명 파싱. 노출마다·루프마다 호출.
- **개선 제안**: `WEATHER_STATUSPATH`(최신 상태 단일 파일)만 읽고 `update_time`으로 stale 판정.

### C19. FilterCheck 결과 반환 및 파일 삭제
- **분류**: Bug
- **파일**: `applications/filtercheck.py` 66, 95, 118~130, 148행
- **문제 요소**: 148행 `problem_units`(마지막 필터만)를 반환(의도는 `final_problematic_units`). 슬루는 alt 80인데 헤더 target은 alt 40으로 기록. `fits_file[0]`은 파일이 없으면 IndexError. 이미지·헤더 삭제 후 빈 폴더 rmdir(파괴적 동작).
- **개선 제안**: 반환값 수정. 테스트 이미지는 별도 폴더에 저장하도록 `IMAGE_PATH` 오버라이드.

### C20. `autofocus_init.py` 절대경로 하드코딩
- **분류**: Hygiene
- **파일**: `applications/autofocus_init.py` 15행
- **문제 요소**: `/home/kds/TCSpy/configuration/filtinfo.dict`. config에 `FTWHEEL_FILTINFOPATH`가 이미 있음. 다른 계정/서버에서 즉시 실패.
- **개선 제안**: `self.config['FTWHEEL_FILTINFOPATH']` 사용.

### C21. NightObservation 루프 내 장시간 `sleep`이 abort를 무시
- **분류**: Concurrency
- **파일**: `applications/nightobservation.py` 331, 361, 423, 456행
- **문제 요소**: 돔 개방 대기 600초, 날씨 불량 200초 동안 `abort_action`을 확인하지 않음.
- **개선 제안**: `abort_action.wait(timeout=600)` 사용.

### C22. 갱신기 스레드가 예외 경로에서 정리되지 않음
- **분류**: Concurrency
- **파일**: `applications/nightobservation.py` 77~79, 399, 408, 466행
- **문제 요소**: 날씨/안전모니터 갱신기는 non-daemon 스레드. `_process()`가 AbortionException으로 종료되면 `abort_weather.set()`에 도달하지 못해 프로세스가 종료되지 않고 `is_running`도 True.
- **개선 제안**: `try/finally`에서 `abort_weather.set()`, `is_running=False`.

### C23. 디버그 출력·오류 메시지 복붙
- **분류**: Hygiene
- **파일**: `action/level1/slewAltAz.py` 134, 136행("ABCABC", "ABSSAD"); `slewRADec.py` 127, 131행(slew_altaz 표기); `singleobservation.py` 298, 486행("Autofocus is aborted" 오기); `autofocus.py` 230행 `print`.
- **개선 제안**: 제거/수정. 메시지는 `type(self).__name__` 기반 템플릿으로.

### C24. 상태 dict 키 오타와 타입 불일치
- **분류**: Bug
- **파일**: `devices/mount/mainmount_pwi4.py` 146~160행
- **문제 요소**: 149행 `status['dec_dec']`(의도 `dec_deg`). `alt/az/jd`는 문자열, `ra/dec`는 float → 소비자가 매번 `float()`. 마운트 Alpaca 구현과도 타입 다름.
- **개선 제안**: 모두 float. 상태 스키마를 `dataclass`로 정의.

### C25. `TelescopeStatus`가 반환하지 않는 상태값 분기
- **분류**: Hygiene
- **파일**: `action/level1/slewRADec.py` 107, `slewAltAz.py` 108, `trackingon.py` 84, `trackingoff.py` 83행
- **문제 요소**: `status_mount == 'parked'` 분기가 있지만 `TelescopeStatus.mount`는 `parked`를 반환하지 않음(포커서만 반환). 죽은 분기.
- **개선 제안**: 상태 Enum 도입 후 분기 정리.

### C26. `MultiTelescopes._all_logs()`의 클래스 반환
- **분류**: Bug / Design
- **파일**: `devices/multitelescopes.py` 200~211행
- **문제 요소**: 인스턴스가 아닌 클래스를 반환하고 메서드에 `self`가 없음. `info/warning/critical`만 있어 `.error()`, `.exception()` 호출 시 AttributeError.
- **개선 제안**: `logging.Logger`에 여러 핸들러를 붙이거나 `LoggerAdapter` 사용.

---

## 5. Low / 저장소 정리

### D1. 빌드 산출물·OS 파일이 git에 추적됨
- **분류**: Hygiene
- `.pyc` 434개, `.DS_Store` 18개, `tcspy.egg-info/`, `output.png`, `tauts`(터미널 덤프), `devices/mount/~/7DT/log/...`(틸드가 확장되지 않은 디렉터리), `utils/alert_history/`, `utils/databases/tiles/*.png` 50여 장. `.gitignore`는 `.codegpt` 한 줄.
- **개선 제안**: 표준 Python `.gitignore` 적용 후 `git rm -r --cached`.

### D2. `interfaces/`의 `abstractclassmethod` 사용
- **분류**: Hygiene
- Python 3.3부터 deprecated. `@classmethod @abstractmethod` 조합 또는 단순 `abstractmethod`.

### D3. 패키징 메타데이터
- **분류**: Hygiene
- `setup.py` url이 `tippy` 저장소, 버전 `1.0.5` vs config `TCSPY_VERSION='Version 1.0'`. `requirements.txt`에 `descartes`(shapely 2와 비호환, 미유지)·`PyQt5`(데모 `status_monitor.py`에만 사용)·`mysql_connector_repackaged`(구버전) 고정.

### D4. 문서/주석 불일치
- **분류**: Hygiene
- `home.py` docstring이 Park 설명, `mainswitch.py` docstring이 SafetyMonitor 복사, `maincamera.warm()` 로그 "Start warning...", `mainmount_alpaca.tracking_on` docstring에 한글 오타("Turnㄴ").

### D5. bare `except:` 광범위 사용
- **분류**: Design / Hygiene
- 장치 모듈·액션·브로커 전반. 원인 은폐가 A1, A5, B8 등 여러 문제의 근원.
- **개선 제안**: `except Exception as e: log.exception(...)` 최소 형태로 교체. ruff `E722`.

### D6. Level1 액션 16개의 보일러플레이트 중복
- **분류**: Design
- 각 분기마다 `log / shared_memory['exception'] / is_running=False / raise` 6줄이 반복(파일당 10회 이상). 복붙 과정에서 A6, A7, B6, B18 같은 불일치가 생김.
- **개선 제안**: `BaseAction` 클래스에 `_fail(exc_type, msg)`, `_finish()` 및 컨텍스트 매니저 제공. 약 1,000줄 감소 예상.

### D7. 테스트 부재
- **분류**: Design
- 저장소에 테스트가 없음. Alpaca 시뮬레이터(ASCOM Omni/Alpaca Simulators)와 PWI4 virtual camera를 이용한 액션 단위 테스트, `TelescopeStatus`·`SingleTarget`·`_scorer`의 순수 함수 테스트를 우선 권장.

### D8. 사용되지 않는 import/변수
- **분류**: Hygiene
- `utils/status_monitor.py`는 PyQt 데모(더미 데이터). `applications/filtercheck.py` 23행 `from tcspy.devices import multitelescopes`. `deepobservation._format_params`. `DB_dynamic._get_target_observable`.

---

## 6. 구조적 개선 제안 (우선순위 순)

1. **상태 정리 일원화**: 모든 액션/앱의 `run()`·`_process()`를 `try/except/finally`로 감싸 `is_running`, `shared_memory['exception']`을 한 곳에서 기록. A1, A3, A4, B18, C22를 한 번에 해결.
2. **프로세스 모델 단순화**: 액션별 `Manager()` 제거. `ProcessPoolExecutor` 또는 단일 Manager 주입. B1.
3. **장치 추상 베이스 클래스**: `BaseMount`, `BaseFocuser`, `BaseCamera`에 락/idle/status 스키마를 두고 PWI4/Alpaca가 상속. B13, C24.
4. **상태값 Enum 화**: `DeviceState.IDLE/BUSY/DISCONNECTED/PARKED`. A5, B5(오타), C25.
5. **안전 판정 fail-closed 통일**: `is_safe()` 단일 함수, `None`은 unsafe. A8, B14.
6. **비밀정보 분리 + 히스토리 정리**: A9.
7. **설정 생성 스크립트 안전장치**: A10.
8. **스케줄러 경쟁/기아 해소**: dispatch 시 동기 `scheduled` 기록, 자원 조건 반영한 target 선택. B2, B4.
9. **폴링 비용 절감**: 날씨 단일 파일, 상태 캐시, 프레임당 1회 조회. C6, C18.
10. **저장소 위생 + 린터 도입**: ruff(E722, B, F) + pre-commit. 여기서 지적한 오타/미정의 변수/사용되지 않는 예외 대부분이 자동 검출됨.

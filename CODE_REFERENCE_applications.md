# applications/ 참조

← [인덱스로](CODE_REFERENCE.md)

`__init__.py` export 순서(중요): `Startup, Shutdown, NightObservation, BiasAcquisition, DarkAcquisition, FlatAcquisition, FilterCheck, AutofocusInitializer`. `AppScheduler`는 미export (스크립트 실행 전용).

**공통 패턴**: `App(multitelescopes, abort_action)` → `run(**kw)`가 Thread로 `_process` 실행(비블로킹; FilterCheck만 join) → `_process`: register_logfile → statusfile 'busy' → MultiAction 배치들 → 'idle'. `abort()`: abort_action.set() (+is_running=False). 대부분 `__main__`에서 Slack 스레드(`7DT Observation on {tonight}` 부모 메시지)에 triggered/finished 게시.

## 1. NightObservation (`nightobservation.py`, 601줄) — 야간 관측 엔진

```python
NightObservation(MultiTelescopes, abort_action)   # 생성 시 initialize() 자동 실행
```

### 초기화
- `self.DB = DB(utctime=now).Dynamic` — 동적 타겟 테이블.
- `self.obsnight = NightSession(now).obsnight_utc`.
- `weather`/`safetymonitor`: **첫 번째 unit의 것을 공용 사용**. `initialize()`에서 각각 `run(abort_action)` 갱신 Thread 시작.
- `NIGHTOBS_SAFETYPE`에 따라 `is_safe` 바인딩: 'WEATHER'→weather, 'SAFETYMONITOR'→safetymonitor, 그 외→항상 True.
- 전체 unit이 `_is_tel_ready`(mount/camera/filterwheel/focuser 모두 IDLE) 통과해야 함. 아니면 `DeviceNotReadyException`.
- 큐: `action_queue`(실행 중 관측 기록 리스트: {target, action, telescope, id, kwargs}), `tel_queue`(유휴 unit dict) — 각각 multiprocessing.Lock 보호.
- **abort 이벤트 2개 분리**: `_observation_abort`(일반), `_ToO_abort`(ToO). 사용 후 fresh Event()로 교체 (clear() 안 씀).
- `autofocus_config()`: use_history=True, history_duration=60, before_start=True, when_filterchange=True, when_elapsed=True, elapsed_duration=60. 이 객체 속성을 바꾸면 이후 디스패치되는 관측에 반영됨.

### dispatch_observation(target, abort_action, observation_status=None)
obsmode 분기:
| obsmode | 조건 | 액션 |
|---|---|---|
| COLOR / SPEC | **전체 unit 유휴일 때만** | ColorObservation / SpecObservation (전체 unit) |
| DEEP | `len(tel_queue) >= target['ntelescope']` | 필요한 만큼 pop → DeepObservation |
| SEARCH / 기타 | unit 1개 이상 유휴 | 1개 pop → SingleObservation |

조건 미충족 시 아무것도 안 함(메인 루프가 재시도). kwargs에는 타겟 필드 + autofocus 정책 + observation_status 포함. 재개 시(observation_status 有) 관측 가능성 재확인 후 불가면 False.

**디더링 연동 (2026-08 추가)**: Dynamic 테이블에 `DITHER_OFFSET_ARCSEC` 컬럼이 있고 값이 유효(float 변환 가능, None/''/'--' 아님)하면 `kwargs['dither_offset_arcsec']`로 전달 → level3/SingleObservation의 스파이럴 디더링 활성화. 컬럼이 없거나 값이 비면 None(디더링 없음).

### execute_observation(action, telescopes, kwargs, target, observation_status, check_visibility=False)
관측 supervisor thread: (옵션) 가시성 체크(불가→DB 'unobservable') → DB status='scheduled'+obs_starttime → statusfile busy → `Process(target=action.run, kwargs)` 실행 → 종료 후 `shared_memory['exception']`에 따라 DB status = observed / aborted / failed (+export_to_csv) → action_queue에서 제거, unit 반환.

### _process() 메인 루프 (sunset_observation → sunrise_observation)
1. 일몰 대기 (5초 폴링, abort 체크).
2. 루프마다: `DB.initialize(initialize_all=False)` (신규 타겟 반영) → `is_safe()` 체크.
3. **안전 시**:
   - 이전 날씨 중단 관측(aborted_action)이 있으면: 600초 대기("dome open") 후 각각 `execute_observation(check_visibility=True)`로 재개.
   - 아니면 `best_target(now)`:
     - rapid ToO 타겟이면: 직전 ToO 트리거로부터 1800초(30분) 경과 시 `_ToOobservation()` 진입(블로킹). 미경과면 `best_target(force_non_ToO=True)`로 일반 타겟 디스패치.
     - 일반 타겟이면 `dispatch_observation(target, self._observation_abort)`.
4. **불안전 시**: `_abort_observation()`(진행 상황 스냅샷 저장 → 재개용) → `_observation_abort` 새 Event로 교체 → `Shutdown(...).run(fanoff=False, slew=True, warm=False)`(파킹만; 냉각/팬 유지) → sleep 200초.
5. 일출 후: 잔여 관측 abort → Shutdown(파킹만).

### _ToOobservation() — ToO 선점 서브 루프
1. `is_rapidToO_triggered=True` → `_abort_observation()`으로 **일반 관측 전부 중단** (unit별 진행 상황 = observation_status 기록).
2. ToO 루프: `best_target()`이 rapid ToO를 반환하는 동안 `_ToO_abort`로 디스패치 반복. 매 트리거마다 `last_rapidToO_trigger_time` 갱신(30분 스로틀 무장). 종료 조건: 타겟 없음 / 외부에서 `is_rapidToO_triggered` 해제 / best가 일반 타겟.
3. 불안전 시 `_abort_ToO()` + Shutdown(파킹만).
4. 종료 후 action_queue 빌 때까지 대기 → **저장해둔 일반 관측들을 `check_visibility=True` + 저장된 observation_status로 재개** (해당 unit들이 모두 유휴일 때만).

### 스레드/프로세스 모델
- Thread: `_process` 1, weather/safetymonitor 갱신 2, 관측당 supervisor 1.
- Process: 관측당 `action.run` 1 (그 안에서 MultiAction이 unit당 Process 추가 생성).

### 버그
- `abort()` 255행: `aborted_action, aborted_observation_status = None` → **TypeError. abort() 깨져 있음.**

## 2. AppScheduler (`appscheduler.py`, 418줄) — 하룻밤 오케스트레이터

`schedule` 라이브러리 기반. `AppScheduler(multitelescopes, abort_action)`.

- `schedule_app(runner_func, start_time(Time, 로컬), **kwargs)` → `schedule.every().day.at("HH:MM").do(...)`. 시각은 `obsnight_ltc`(로컬), 비교는 `obsnight_utc`.
- 러너 메서드: `run_startup / run_filtercheck / run_autofocus_init / run_nightobs / run_bias / run_dark / run_flat / run_shutdown` — 공통적으로 `thread_lock`으로 직렬화, Slack triggered/finished 게시, `is_running` 폴링 대기, 1회 실행 후 `schedule.CancelJob` 반환.
- `run_nightobs`는 종료 후 `DB().Dynamic.export_to_csv(save_type='history')`로 그날 테이블 아카이브.
- `get_obsinfo_tonight(tonight_str, key_for_set=['exptime','xbinning','gain'])`: `APPSCHEDULER_SEARCHKEY` 글롭 + ccdproc ImageFileCollection으로 그날 LIGHT 프레임의 유니크 설정 목록 추출 → 다크/바이어스 파라미터 결정.
- `run_schedule()`: 모든 job이 실행/취소될 때까지 블로킹.

### `__main__` 타임라인
1. sunset_startup: Startup(connect/home/slew/cool=True).
2. sunset_flat: FilterCheck(exptime=60).
3. sunset_flat+15분, +25분: AutofocusInitializer('specall', search_focus_range=3000) ×2.
4. sunset_observation: NightObservation. → run_schedule() (밤새 블로킹).
5. sunrise_flat: FlatAcquisition(count=9, gain=2750).
6. sunrise_shutdown+10분부터: 설정 조합별 DarkAcquisition (간격 = exptime*count*1.3초).
7. 마지막 다크 +15분부터: (binning,gain)별 BiasAcquisition (10분 간격).
8. 마지막 바이어스 +20분: Shutdown(fanoff/slew/warm=True).

버그: `set_alert_sender()`에서 미정의 `alert_slack` 참조 가능 (NameError).

## 3. Startup (`startup.py`)

```python
run(connect=False, fanon=True, home=True, slew=True, cool=True)
```
단계 순서 (각각 MultiAction; 실패 unit은 `multitelescopes.remove()`, 전멸 시 ActionFailedException, abort 시 AbortionException):
1. Connect
2. FansOn — **하드코딩: '7DT02' 존재 시 7DT02/7DT06 제외 + `params_fanson[:-1]` 슬라이스**
3. Home (+sleep 10초)
4. SlewAltAz(STARTUP_ALT=30, STARTUP_AZ=90)
5. Cool(STARTUP_CCDTEMP=-10, tolerance=1)

## 4. Shutdown (`shutdown.py`)

```python
run(fanoff=True, slew=True, warm=True)
```
1. FansOff (전체 unit — Startup과 달리 제외 없음)
2. SlewAltAz(SHUTDOWN_ALT=30, SHUTDOWN_AZ=90)
3. Warm(SHUTDOWN_CCDTEMP=+10, tolerance=1)

**NightObservation에서는 항상 `run(fanoff=False, slew=True, warm=False)`** — 파킹만 하고 팬/냉각 유지 (날씨 회복 시 빠른 재개).

## 5. 캘리브레이션·점검 앱

### BiasAcquisition
`run(count=9, binning=1, gain=2750)` — 시퀀스 전체가 공유하는 `id_=uuid4().hex`. 프레임 인덱스별로 MultiAction(Exposure: exptime=0, imgtype='BIAS', filter_=None) — 전 unit 동시 1장씩.

### DarkAcquisition
`run(count=9, exptime=100, binning=1, gain=2750)` — Bias와 동일 구조, imgtype='DARK', 실제 exptime 사용.

### FlatAcquisition
`run(count=9, binning=1, gain=2750)` — MultiAction(AutoFlat) 1회. 필터 순회는 AutoFlat 내부(AUTOFLAT_FILTERORDER). 실패 시 unit별 `shared_memory[tel]['status']`(필터별 dict)에서 실패 필터 로그. `abort()`는 AbortionException을 raise함.

### FilterCheck
`run(exptime=1)` — **블로킹(join)**, `self.result` 반환.
흐름: SlewAltAz(alt=80, az=300) → g/r/i 각 1장(Exposure, name='filtercheck') → 각 unit의 `IMAGE_PATH/<night>*/filtercheck*.fits`에서 median 카운트 측정 → **FITS+.head 파일 삭제** → 필터별 5σ 아웃라이어 unit critical 로그.
버그: `self.result=(skylevel_dict, problem_units)` — 마지막 필터의 아웃라이어만 담김(전체 union은 로컬 변수). `__main__`의 IMAGE_SAVELOG 복원이 True 하드코딩.

### AutofocusInitializer (`autofocus_init.py`)
`run(filter_='specall', use_history=True, history_duration=0, search_focus_when_failed=True, search_focus_range=3000, slew=True)`
- `FILTINFO_FILE = '/home/kds/TCSpy/configuration/filtinfo.dict'` **하드코딩 주의**.
- 흐름: (옵션) SlewAltAz(alt=50, az=160, tracking=True — **fresh Event 전달이라 이 단계는 abort 불가**) → `SPECMODE_FOLDER/<filter_>.specmode`(JSON {tel: [filters]})로 unit별 필터 계획 (파일 없으면 filter_를 리터럴 필터로) → 리스트 길이 순환 반복으로 정규화 → 라운드별 MultiAction(AutoFocus). ActionFailedException은 안 잡아서 스레드 밖으로 전파.

## 6. 스크립트류 (모듈 아님, import 시 실행)

- `defocus_test.py` — `#%%` 셀 스크립트. WASP-178b 필드에서 DeepObservation 11회 반복하며 포커스 +100씩 이동, 마지막에 −1100 복원.
- `fanonofftest.py` — 팬 열특성 테스트: 로컬 20:50 off / 01:00 on / 03:00 off / 05:00 on 무한 스케줄.
- `get_target_telescope.py` — SPEC 모드 필터→unit 배정 백트래킹 솔버 프로토타입 (7DT02–12 필터 하드코딩; 어디서도 임포트 안 됨).
- `tmp.py` — 빈 파일.

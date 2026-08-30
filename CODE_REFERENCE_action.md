# action/ 참조

← [인덱스로](CODE_REFERENCE.md)

`action/__init__.py` export: `MultiAction`만.
로그 접두어로 레벨 구분: LV1 `=====`, LV2 `==========`, LV3 `===============`.

## 1. 공통 패턴

### 생성자 (Level1/2)
```python
Action(singletelescope: SingleTelescope, abort_action: multiprocessing.Event)
# self.telescope, self.telescope_status = TelescopeStatus(telescope), self.abort_action
# self.shared_memory = Manager().dict()  → succeeded=False, exception=None, is_running=False
```
Level3는 `(multitelescopes, abort_action)` + `observer`(첫 unit의 것) + `shared_memory['status']`.

### shared_memory 키
| 키 | 의미 |
|---|---|
| `succeeded` | run() 시작 시 False, 완주 시 True |
| `exception` | 예외 클래스명 **문자열** ('ConnectionException'/'AbortionException'/'ActionFailedException') |
| `is_running` | 실행 중 플래그 (호출자가 abort 후 스핀 대기에 사용) |
| `status` | Level2 AutoFlat/SingleObservation, Level3: 필터별/unit별 진행 상황 |

### run() 골격
register_logfile → "LV{n}[Class] is triggered." → is_running=True → `TelescopeStatus`로 디바이스 사전 체크 → abort 체크 → 디바이스 호출(try/except로 예외 변환) → succeeded=True → "is finished." → return True. (예외 없는 실패는 None 반환하는 경우 있음)

### abort() 골격
`abort_action.set()` → 디바이스 `wait_idle()`(L1) 또는 자식 `shared_memory['is_running']` 스핀(L2) 또는 `multiaction.status` 스핀(L3) → warning 로그 → `shared_memory['exception']='AbortionException'` → **항상 `AbortionException` raise** (MultiAction.abort()만 raise 안 함).

### 예외 계약 (핵심)
| 던지는 예외 | 조건 |
|---|---|
| `ConnectionException` | 필요한 디바이스가 'disconnected' |
| `AbortionException` | abort_action set / abort() 호출 |
| `ActionFailedException` | busy/parked/unknown 상태, 디바이스 예외(Slewing/Exposure/Cooling...FailedException) 래핑 |

디바이스별 예외는 절대 상위로 전파되지 않음.

## 2. MultiAction (`multiaction.py`)

```python
MultiAction(array_telescope, array_kwargs: List[dict]|dict, function: 액션클래스, abort_action)
```
- kwargs가 단일 dict면 전 unit에 복제(broadcast), 리스트면 zip.
- **생성자에서** unit당 액션 인스턴스 + `Process(name='Class[tel]', target=func.run, kwargs=...)` 미리 생성. `shared_memory[tel_name] = 자식 액션의 shared_memory`.
- `run()`: **`abort_action.clear()` 먼저**(기존 abort 요청 리셋 주의!) → 전 프로세스 start → 0.1초 폴링. abort set 시 즉시 `AbortionException`(join 안 함). 전 프로세스 종료 후 unit별 `succeeded` 집계 — 하나라도 실패 시 `ActionFailedException`.
- `abort()`: `abort_action.set()`만 (raise 안 함).
- `status` (property): `{'Class[tel]': process.is_alive()}`.
- docstring의 `get_results()`는 **존재하지 않음** — 결과는 shared_memory에서 직접 읽음.

## 3. Level 1 (`action/level1/`) — 16개

| 클래스 | run() | 디바이스 호출 | 비고 |
|---|---|---|---|
| `Connect` | `run()` | 각 device `.connect()` (bare except pass) | 연결 실패해도 critical 로그만 — ConnectionException 안 던짐 |
| `Disconnect` | `run()` | `.disconnect()` | **버그: exception 임포트 누락 → abort 경로 NameError** |
| `ChangeFilter` | `run(filter_)` | `filterwheel.move(filter_)` | 성공 경로에서 shared_memory['is_running'] 안 끔 |
| `ChangeFocus` | `run(position=None, is_relative=False)` | `focuser.get_status()`, `.move(position, abort_action)` | relative면 현재+position |
| `Cool` | `run(settemperature, tolerance=1)` | `camera.cool(...)` | |
| `Warm` | `run(settemperature, tolerance=1)` | `camera.warm(...)` | 버그: disconnected 시 raise 대신 return; 시작 시 is_running=False |
| `Exposure` | `run(frame_number, exptime, obsmode='Single', filter_=None, specmode/colormode=None, ntelescope=1, gain=0, binning=1, imgtype='Light', ra/dec/alt/az, name, objtype, id_, note, comment, is_ToO=False, is_rapidToO=False)` | (필요시) 중첩 `ChangeFilter` → `camera.exposure(...)` → `mainImage(...).save()` | LIGHT는 filter_ 필수. BIAS→exptime=ExposureMin·is_light=False, DARK→is_light=False, FLAT→is_light=True. autofocus_history를 헤더에 포함. 이미지 저장 실패는 bare except → ActionFailedException |
| `FansOn`/`FansOff` | `run()` | `focuser.fans_on()/off()` | |
| `Home` | `run()` | `mount.find_home(abort_action)` | **버그: 실패 시 raise 누락 → UnboundLocalError** |
| `Park` | `run()` | `mount.park(abort_action)` | 같은 raise 누락 버그. MOUNT_PARKALT/PARKAZ 사용 |
| `Unpark` | `run()` | `mount.unpark()` | abort 사전 체크 없음 |
| `SlewAltAz` | `run(alt, az, force_action=False, tracking=False)` | `mount.slew_altaz(...)` | 디버그 print("ABCABC") 잔존 |
| `SlewRADec` | `run(ra, dec, force_action=False)` | `mount.slew_radec(..., tracking=True)` | **tracking 하드코딩 True** |
| `TrackingOn`/`TrackingOff` | `run()` | `mount.tracking_on()/off()` | abort 사전 체크 없음 |

abort() 시 wait_idle() 대상: mount → Park/Home/SlewAltAz/SlewRADec, camera → Cool/Warm/Exposure, focuser → ChangeFocus, filterwheel → ChangeFilter.

## 4. Level 2 (`action/level2/`)

### AutoFocus (mainConfig 상속)
```python
run(filter_=None, use_history=True, history_duration=60, search_focus_when_failed=False, search_focus_range=2000)
```
- 히스토리: `config['AUTOFOCUS_HISTORYPATH']` (unit별 autofocus.history JSON).
- 흐름: camera/focuser/mount/filterwheel 연결 체크 → (필요시) ChangeFilter → **히스토리가 `history_duration`분 내 성공 기록이면 그 포지션으로 이동만 하고 즉시 True 반환** → 아니면 히스토리 위치 적용 후 `focuser.autofocus_start(abort_action)` → 실패 + `search_focus_when_failed`면 ±500씩 확장 그리드 서치(±1000, ∓1500, ..., 2*range//500회) → 전부 실패 시 원위치 복원 후 **None 반환 (예외 없음, is_running이 shared_memory에 True로 남음)**.
- 성공 시 `update_focus_history(filter_, focusval, focuserr, True)` JSON 기록.
- 헬퍼: `history` property, `write_default_focus_history()`.

### AutoFlat
```python
run(count=9, gain=2750, binning=1)
```
- 흐름: weather+safetymonitor 안전 체크(불안전→ActionFailedException) → `SlewAltAz(AUTOFLAT_ALTITUDE/AZIMUTH, tracking=False)` → BIAS 1장으로 bias_level 측정 → `AUTOFLAT_FILTERORDER`∩filtnames 순서(밝은 순)로 필터별:
  - ChangeFilter → 루프: `camera.exposure(FLAT)` → sky_level = mean−bias → `MINCOUNT < sky < MAXCOUNT`면 mainImage 저장(obs_count+=1) → 노출시간 적응 조정 (`exptime = max(0.9*exptime_min + 0.1*exptime_max, MINEXPTIME)`; 너무 어두우면 WAITDURATION 대기, 너무 밝으면 "Sky is too bright" 실패).
- 필터 하나의 ActionFailedException은 로그만 하고 다음 필터 계속. Connection/Abortion은 전체 중단.
- `shared_memory['status']` = {filter: bool}; succeeded = 전 필터 성공.
- 버그: sky_level_acceleration이 항상 0 (동일 변수 뺄셈).

### SingleObservation — 관측 워크호스
```python
run(exptime, count, obsmode='Single', filter_=None, specmode=None, colormode=None,
    ntelescope=1, gain=2750, binning='1', imgtype='Light',
    ra/dec/alt/az, name, objtype, id_, note, comment, is_ToO=False, is_rapidToO=False,
    force_slewing=False,
    autofocus_use_history=True, autofocus_history_duration=60,
    autofocus_before_start=False, autofocus_when_filterchange=False,
    autofocus_when_elapsed=False, autofocus_elapsed_duration=60,
    observation_status: dict = None, **kwargs)
```
- **`exptime`/`count`/`filter_`/`binning`은 콤마 구분 문자열** (예: '5,5', 'g,r') → 다필터 시퀀스. 길이 안 맞으면 첫 원소 브로드캐스트.
- **`observation_status` = 재개 메커니즘**: `{filter: {'triggered': n, 'observed': m}}`. net = triggered−observed만 촬영. `shared_memory['status']`에 게시.
- **`dither_offset_arcsec: float = None` = 디더링** (2026-08 추가): 값이 있으면(>0) 프레임마다 소용돌이 패턴(`generate_dithering_offsets`, 25점 5×5 스파이럴, 26번째부터 순환) 위치로 `mount.offset_radec(set_total, 멱등)` 적용 후 촬영. **PWI4 마운트 + radec 타겟에서만 동작** (아니면 경고 후 디더링 없이 진행). 위치 인덱스 = 해당 필터의 observed 값 → 재개 시 패턴 연속성 유지. 슬루 직후 잔여 오프셋 reset(pwi4 항상), 관측 종료 후에도 reset. 오프셋 실패는 경고만 하고 촬영 계속.
- 흐름: 디바이스 체크 → SingleTarget 구성 → filter_가 'None'(문자열)이면 `exposure_info['specmode_filter'|'colormode_filter'][tel_name]`에서 해석 → coordtype에 따라 SlewRADec/SlewAltAz → (옵션) autofocus_before_start (ActionFailed는 **무시하고 진행**) → 필터별 루프: 현재 필터와 다르면 ChangeFilter (+옵션 when_filterchange AutoFocus) → count만큼 Exposure (frame_number = observed값) → observed 증가.
- when_elapsed: AutoFocus history의 update_time이 elapsed_duration분보다 오래됐거나 실패 기록이면 `AutoFocus(use_history=False)` 실행.
- 반환: `all(result_all_exposure)`.
- 주의: `shared_memory['is_running']` 초기값이 True (다른 액션과 불일치).

## 5. Level 3 (`action/level3/`)

셋 다 동일 템플릿:
1. `SingleTarget`으로 `exposure_params`/`target_params` 생성.
2. unit별 kwargs 구성 (autofocus 정책, `dither_offset_arcsec`, observation_status[tel_name] 전달 포함).
3. `MultiAction(devices.values(), kwargs, SingleObservation, abort_action)` 실행. `shared_memory['status'] = multiaction.shared_memory`.
4. AbortionException → self.abort(); ActionFailedException → unit별 성공/실패 로그 후 재raise.

| 클래스 | run() 고유 파라미터 | 필터 결정 방식 |
|---|---|---|
| `SpecObservation` | `specmode` (예: 'specall') | `specmode_filter[tel_name]` — unit마다 다른 필터 (분광 모드) |
| `DeepObservation` | `filter_`, `ntelescope`(devices 수로 덮어씀) | 전 unit 동일 filter_ (깊이 우선) |
| `ColorObservation` | `colormode` (예: 'gri') | `colormode_filter[tel_name]` (색 분산) |

공통 버그: `'dicconnected'` 오타(연결 사전 체크 무력화), `autofocus_elapsed_time=` 이름 불일치(**kwargs로 삼켜져 기본 60 사용), `all(dict-of-dicts)` 항상 truthy. `ColorObservation`은 `__init__`에서 `self.multiaction` 미초기화 → run() 전 abort() 호출 시 AttributeError.

## 6. 호출 관계

```
SpecObservation ─┐
DeepObservation ─┼─ MultiAction ─▶ SingleObservation ─┬▶ SlewRADec/SlewAltAz ▶ mount
ColorObservation ┘                                    ├▶ ChangeFilter ▶ filterwheel.move
                                                      ├▶ Exposure ─┬▶ camera.exposure + mainImage
                                                      │            └▶ ChangeFilter
                                                      └▶ AutoFocus ─┬▶ ChangeFocus ▶ focuser.move
                                                                    ├▶ ChangeFilter
                                                                    └▶ focuser.autofocus_start
AutoFlat ─┬▶ SlewAltAz
          ├▶ ChangeFilter
          └▶ camera.exposure (Exposure 액션 우회, 직접 호출)
```

`test.py`(action/, level1/)는 스크래치 스크립트 — 모듈 아님.

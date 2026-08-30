# devices/ 참조

← [인덱스로](CODE_REFERENCE.md)

`devices/__init__.py` export: `PWI4`, `SingleTelescope`, `TelescopeStatus`, `MultiTelescopes` (임포트 순서 의존 — SingleTelescope가 먼저 바인딩되어야 함).

## 1. SingleTelescope (`singletelescope.py`)

한 unit의 모든 디바이스를 묶는 객체. `mainConfig` 상속.

```python
SingleTelescope(unitnum: int)
```

| 속성 | 내용 |
|---|---|
| `camera` | `mainCamera` (Alpaca) |
| `mount` | `mainMount_Alpaca` 또는 `mainMount_pwi4` (`MOUNT_DEVICETYPE`) |
| `focuser` | `mainFocuser_Alpaca` 또는 `mainFocuser_pwi4` (`FOCUSER_DEVICETYPE`) |
| `filterwheel` | `mainFilterwheel` (Alpaca) |
| `weather` / `safetymonitor` | `mainWeather` / `mainSafetyMonitor` (사이트 공용 장비) |
| `observer` | `mainObserver` |
| `name` / `tel_name` | 예: '7DT01' |
| `switch` | **주석 처리됨** (mainSwitch 미사용) |

- `status` (property): 모든 디바이스 `get_status()` 갱신 후 dict 반환 (keys: camera, mount, focuser, filterwheel, weather, safetymonitor, observer).
- `devices` (property): 디바이스 객체 dict (observer 제외).
- `update_statusfile(status='idle'|'busy', do_trigger=True)`: `MULTITELESCOPES_FILE`에 portalocker 잠금으로 `Status`/`Status_update_time` 기록.
- `register_logfile()`: mainLogger 생성. **버그: None 반환 → `__init__`의 `self.log = self.register_logfile()`이 log를 None으로 만듦.**
- `_get_mount()`/`_get_focuser()`: 미지원 타입일 때 `TelTypeError`/`FocuserTypeError`를 raise가 아닌 **return**.

## 2. MultiTelescopes (`multitelescopes.py`)

```python
MultiTelescopes(SingleTelescope_list: List[SingleTelescope] = None)
```

- 리스트 미지정 시 `_load_from_config()`: `MULTITELESCOPES_FILE`(JSON)에서 Mount/Focuser/Camera/Filterwheel 모두 `is_active`인 unit만 `SingleTelescope(unitnum)` 생성 (unit 번호는 이름 끝 2자리 정규식).
- `devices`: dict name→SingleTelescope. `observer`: mainObserver.
- `status` (property): unit당 Thread 하나로 `TelescopeStatus(tel).dict` 병렬 수집.
- `log`: 전 unit 로거에 브로드캐스트하는 객체 (`.info/.warning/.critical`). `log_dict`: unit별 로거.
- `add(tel)` (**버그: `_devices_list` 미갱신 → status/filters에 안 보임**), `remove(name)`, `update_statusfile(...)`(전체 unit), `register_logfile()`, `filters`(unit별 filtnames).

### multitelescopes.dict 구조
```json
{"7DT01": {"Status": "idle|busy", "Status_update_time": "<ISOT>",
  "Mount": {"is_active": true, "name": "...", "timestamp": "..."},
  "Focuser": {...}, "Camera": {...}, "Filterwheel": {...}}}
```

## 3. TelescopeStatus (`telescopestatus.py`)

`TelescopeStatus(singletelescope)` — 디바이스별 한 단어 상태. **모든 property가 try/except로 감싸져 절대 raise하지 않음** (기본 `'disconnected'`).

| property | 값 | 비고 |
|---|---|---|
| `.dict` | camera/mount/filterwheel/focuser/dome/safetymonitor/weather | |
| `camera` | idle/busy/disconnected | ThreadPool 5초 타임아웃으로 Alpaca `CameraState` 조회 (0→idle) |
| `mount` | idle/busy/disconnected | Alpaca: Connected/AtHome/AtPark/Slewing/Tracking 순차 체크(뒤가 앞을 덮음). PWI4: `mount.device.status()` 검사. **버그: 존재하지 않는 `axis2` 참조 → 조용히 삼켜짐.** 'parked'는 실제 반환 안 됨 (level1의 'parked' 분기는 dead code) |
| `filterwheel` | 항상 'idle' | 연결 체크 주석 처리됨 |
| `focuser` | idle/busy/disconnected/parked | parked는 PWI4 전용 (is_enabled=False) |
| `dome` | 하드코딩 'disconnected' | |
| `weather`/`safetymonitor` | safe/unsafe/disconnected | `@Timeout(3)` + `get_status()`의 is_connected/is_safe |

## 4. pwi4_client.py — PWI4 HTTP 클라이언트

PlaneWave PWI4용 vendored 클라이언트 (stdlib만 사용, 기본 `localhost:8220`, HTTP 타임아웃 3초).

### PWI4 주요 메서드
- 마운트: `status()`, `mount_connect/disconnect()`, `mount_enable/disable(axisNum)`, `mount_find_home()`, `mount_stop()`, `mount_goto_ra_dec_apparent/j2000(ra_hours, dec_degs)`, `mount_goto_alt_az(alt_degs, az_degs)`, `mount_offset(**kw)`, `mount_park()`, `mount_set_park_here()`, `mount_tracking_on/off()`, `mount_follow_tle(...)`, 포인팅 모델 `mount_model_*`.
- 포커서: `focuser_connect/disconnect/enable/disable()`, `focuser_goto(target)`, `focuser_stop()`.
- **TCSpy 수동 추가분**: `autofocus_start()`, `autofocus_stop()`, `fans_on()`, `fans_off()`.
- `mount_offset(**kwargs)`: 축(ra/dec/axis0/axis1/path/transverse) × 접미사(`_reset`, `_add_arcsec`, `_set_total_arcsec`, `_set_rate_arcsec_per_sec` 등) 조합으로 포인팅 오프셋 제어. 디더링 구현이 사용.
- 기타: rotator/M3/virtualcamera 메서드.

### PWI4Status (status() 반환)
`key=value` 응답을 속성 트리로 래핑: `mount.is_connected/is_slewing/is_tracking/azimuth_degs/altitude_degs/ra_j2000_hours/dec_j2000_degs/...`, `mount.axis0/axis1.is_enabled/rms_error_arcsec/...` (**axis2는 없음**), `focuser.exists/is_connected/is_enabled/position/is_moving`, `autofocus.is_running/success/best_position/tolerance`, `site.*`, `rotator.*`, `m3.port`.

버그: HTTP 오류 메시지 조합에서 str+bytes 연결 → TypeError로 원 오류가 가려질 수 있음.

## 5. observer/mainobserver.py — mainObserver

```python
mainObserver()   # 전역 config만 사용
```
astroplan.Observer + astropy 좌표 래핑 (사이트: 칠레, config OBSERVER_*).

| 메서드 | 내용 |
|---|---|
| `get_status()` | update_time, jd, 사이트 정보, moonphase, is_connected 등 dict |
| `localtime(dt)` | UTC→사이트 로컬 (pytz) |
| `siderialtime(t, mode='mean')` | 지역 항성시 |
| `is_night(t)` | -18° 기준 |
| `tonight(t, horizon=-18)` | (일몰, 일출) Time 튜플 |
| `sun_risetime/settime(t, mode='nearest', horizon=-18)` | 태양 출몰 |
| `sun_radec/altaz(t)`, `moon_radec/altaz(t)`, `moon_risetime/settime`, `moon_phase(t)` | 태양/달 |

## 6. switch/mainswitch.py — mainSwitch

`mainSwitch(unitnum)` — Alpaca Switch 래퍼. `SWITCH_KEY_*` 문자열을 스위치 설명(description)에 **부분 문자열 매칭**해 논리 디바이스명→스위치 인덱스 매핑.
- `switch_on(device_type)` / `switch_off(device_type)` — 'MOUNT'/'FOCUSER'/'CAMERA' (대소문자 무관).
- `get_status()`는 더미 `{}`.
- 현재 SingleTelescope에서 **미사용** (주석 처리).

## 7. 개별 디바이스 모듈 (camera/mount/focuser/filterwheel/weather/safetymonitor)

각 `main*.py`가 `connect()/disconnect()/get_status()` + 고유 동작 제공, 실패 시 `tcspy.utils.exception`의 디바이스별 예외 raise:
- `mainCamera`: `exposure(exptime, imgtype, binning, is_light, gain, abort_action)`, `cool/warm(settemperature, tolerance, abort_action)`, `wait_idle()`, `device.ExposureMin` 등.
- `mainMount_*`: `slew_radec(ra, dec, abort_action, tracking, force_action)`, `slew_altaz(...)`, `park/unpark()`, `find_home()`, `tracking_on/off()`, `wait_idle()`.
  - `mainMount_pwi4` 전용 (2026-08 추가, 디더링용): `offset_radec(ra_arcsec, dec_arcsec, is_relative=False)` — PWI4 `mount_offset`의 `ra/dec_set_total_arcsec`(기본, 멱등) 또는 `_add_arcsec`(relative) 사용, settle 대기 포함, 실패 시 `SlewingFailedException`; `reset_offset()` — `ra/dec_reset`으로 누적 오프셋 해제. Alpaca 마운트에는 없음.
- `mainFocuser_*`: `move(position, abort_action)`, `autofocus_start(abort_action)`, `fans_on/off()`, `get_status()['position']`, `wait_idle()`.
- `mainFilterwheel`: `move(filter_)`, `get_status()['filter_']`, `filtnames`, `wait_idle()`.
- `mainWeather`/`mainSafetyMonitor`: `get_status()['is_safe'/'is_connected']`, `run(abort_action)` (연속 갱신 루프 — NightObservation이 Thread로 구동).

## 8. 기타/깨진 파일

- `power.py` — 스크래치 스크립트. **import 시 즉시 `10.0.106.6:11111` 접속 시도. 임포트 금지.**
- `dome/__init__.py`, `rotator/__init__.py` — 존재하지 않는 모듈(`maindome`, `mainrotator`)을 import → ImportError.
- `observer/__init__.py` — 빈 파일 (mainObserver는 `tcspy.devices.observer.mainobserver`에서 직접 임포트하는 코드도 있음).

# utils/ 참조 (databases·target·alertmanager 제외)

← [인덱스로](CODE_REFERENCE.md) · DB/타겟은 [CODE_REFERENCE_databases.md](CODE_REFERENCE_databases.md) · 알림은 [CODE_REFERENCE_alertmanager.md](CODE_REFERENCE_alertmanager.md)

`utils/__init__.py` export: `Timeout`, `NightSession`만. 나머지는 서브패키지 경로로 임포트 (예: `from tcspy.utils.connector import SlackConnector`).

## 1. NightSession (`nightsession.py`)

```python
NightSession(utctime: Time = Time.now())   # 기본값이 임포트 시점에 고정됨 — 항상 명시적으로 전달할 것
```
- `obsnight_utc` / `obsnight_ltc`: 밤 이벤트 시각 객체 (ltc는 사이트 로컬 변환, naive datetime).
- **계산 방식**: 앵커 = `sunrise_shutdown = observer.tonight(utctime, horizon=+10°)[1]` (아침 shutdown 시각). **다른 모든 이벤트는 이 앵커에서 `mode='previous'`로 역산** → 같은 밤에 속함이 보장됨.
- 속성 (모두 astropy Time):

| 속성 | horizon | 의미 |
|---|---|---|
| `sunrise_shutdown` | +10° (`NIGHTSESSION_SUNALT_SHUTDOWN`) | 앵커, 아침 셧다운 |
| `sunrise/sunset_civil` | 0° | 기하학적 일출/일몰 |
| `sunrise/sunset_nautical` | -6° | (이름과 달리 시민박명) |
| `sunrise/sunset_astro` | -12° | (이름과 달리 항해박명) |
| `sunrise/sunset_night` | -18° | 천문박명 (진짜 밤) |
| `sunrise/sunset_flat` | -8° (`_AUTOFLAT`) | 플랫 촬영 창 |
| `sunrise/sunset_startup` | -6° (`_STARTUP`) | 스타트업 |
| `sunrise/sunset_observation` | -15° (`_OBSERVATION`) | 과학 관측 창 |
| `midnight` | — | -12° 박명 구간 중점 (jd) |
| `observable_hour` | — | 관측 창 길이(시간) |

주의: 이름과 통상적인 박명 정의가 한 단계씩 어긋나 있음 (nautical=-6은 보통 civil).

## 2. Timeout (`timeout.py`)

`@Timeout(timeout_sec, error_msg)` 데코레이터 — 데몬 스레드에서 함수 실행 후 `join(timeout)`. 초과/예외 시 Exception raise. **워커 스레드는 죽지 않고 계속 돌아감** (데몬이라 프로세스 종료 시 정리). 디바이스 드라이버 전반에서 사용 (mount 5s, weather 15s, telescopestatus 3s 등).

## 3. connector/

`__init__.py`: `GoogleSheetConnector`, `SlackConnector`, `SQLConnector`, `GmailConnector`.

### SlackConnector (`slackconnector.py`)
```python
SlackConnector(token_path='~/.config/slack/slack_token_7dt_obseration_alert.txt',
               default_channel_id='C07SREPTWFM')
```
- `get_message_ts(match_string)` — 채널 히스토리에서 문자열 포함 첫 메시지의 ts (없으면 None).
- `post_message(text, blocks)` / `post_thread_message(message_ts, text, blocks)`.
- `select_channel(name)`, `get_channel_id(name)` (공개+비공개 채널 검색).
- 야간 운영 알림 관례: `7DT Observation on {tonight_str}` 부모 메시지의 스레드에 각 앱이 triggered/finished 게시.

### GmailConnector (`gmailconnector.py`)
```python
GmailConnector(user_account, user_token_path=None)  # Gmail 앱 비밀번호 텍스트 파일
```
- `send_mail(to_users, cc_users, subject, body, attachments=None, text_type='plain'|'html')` — SMTP(starttls 587), 실패 시 재로그인 후 1회 재시도.
- `read_mail(mailbox='inbox', max_numbers=10, since_days=5, save=True, save_dir='../alert_history/gmail')` → `[{'From':(이름,주소), 'Subject', 'Date', 'Body', 'Attachments':[저장경로]}]`. 저장 구조: `<save_dir>/<YYYYmmdd_HHMMSS>/{body.txt, attachments/}`.
- `ensure_logged_in_imap()/smtp()`, `login_*`/`logout_*`.
- 버그: `__repr__`(미존재 `logged_in` 참조), `delete_mail`(미존재 `ensure_logged_in()` 호출).

### GoogleSheetConnector (`GSconnector.py`)
```python
GoogleSheetConnector(spreadsheet_url=..., authorize_json_file=<service account JSON>, scope=[...])
```
- `read_sheet(sheet_name, format_='Table'|'PANDAS'|'DICT', save=False, save_dir)` — 첫 행이 헤더.
- `write_sheet(sheet_name, data, append=True, clear_header=False)` — DataFrame/Table/dict 지원, 없으면 시트 생성(1000×40).
- `clear_sheet(sheet_name, clear_header=False)`, `get_sheet_list()`.
- 버그: `__repr__`이 미존재 `_get_sheet_list()` 호출.

### SQLConnector (`SQLconnector.py`)
```python
SQLConnector(id_user='hhchoi', pwd_user=<하드코딩>, host_user='localhost', db_name='target', pool_size=16)
```
MySQL 커넥션 풀 기반.
- `execute(sql, params=None, commit=False)` — buffered cursor 반환 (연결은 finally에서 반납).
- `get_data(tbl, select_key='*', where_value=None, where_key='id', out_format='Table'|'dict')`.
- `insert_rows(tbl, data: Table)` — 행 단위 INSERT (idx 컬럼 제거, DB 컬럼과 교집합만, ''→NULL).
- `update_row(tbl, update_value, update_key, id_value, id_key=['id'])` — 스칼라 또는 리스트 쌍.
- `set_data_id(tbl, update_all=False)` — 빈 id에 uuid4().hex 발급 (idx 기준 매칭).
- `remove_rows(tbl, ids)`, `tables`/`databases` property, `get_colnames`, `change_db/create_db/remove_db`.

## 4. logger/

### mainLogger (`mainlogger.py`)
```python
mainLogger(unitnum, logger_name).log()  # → logging.Logger
```
- 같은 이름 로거에 핸들러가 이미 있으면 그대로 반환 (중복 방지).
- StreamHandler + (LOGGER_SAVE=True면) FileHandler.
- **로그 파일명: `(Time.now() - 12h).strftime('%Y%m%d') + '.log'`** — UTC 정오 롤오버로 한 밤 = 한 파일. 위치: `LOGGER_PATH`.

### LogFormat (`logformat.py`)
`LogFormat(msg).message_with_border(width=60, border_char='=')` — 배너형 로그 문자열.

## 5. image/ — mainImage (`mainimage.py`)

```python
mainImage(frame_number, config_info, image_info, camera_info=None, mount_info=None,
          filterwheel_info=None, focuser_info=None, observer_info=None,
          target_info=None, weather_info=None, autofocus_info=None)
```
- FITS PrimaryHDU 조립. 헤더는 각 info dict에서 병합 — **없는 정보도 빈 카드로 키는 항상 존재**.
- 설정은 `config_info` dict 주입으로 받음 (mainConfig.__init__ 호출 안 함).

### 주요 FITS 헤더 키
| 그룹 | 키 |
|---|---|
| 포인팅 | `AIRMASS`(Pickering 2002), `ALTITUDE/CENTALT`, `AZIMUTH/CENTAZ`, `RA`, `DEC` |
| 카메라 | `INSTRUME`, `GAIN`, `EGAIN`, `CCD-TEMP`, `SET-TEMP`, `COLPOWER` |
| 포커스 | `FOCUSPOS`; 오토포커스: `AFTIME`, `AFVALUE`, `AFERROR` |
| 필터 | `FILTER` |
| 이미지 | `IMAGEID`, `IMAGETYP`, `EXPTIME`/`EXPOSURE`, `DATE-OBS`(UTC), `DATE-LOC`, `JD`, `MJD`, `XBINNING`, `YBINNING` |
| 타겟 | `OBJECT`, `OBJTYPE`, `OBJCTRA/DEC`(hms/dms), `OBJCTRA_/DE_`(deg), `OBJCTALT/AZ/HA`, `OBJCTID`, `MOONSEP`, `OBSMODE`, `SPECMODE`, `NTELSCOP`, `NOTE`, `IS_ToO`, `RAPIDToO` |
| 하드웨어 | `TELESCOP`, `MNT_*`, `CAM_*`, `FILT_*`, `FOC_*`, `FOCALLEN`, `APTDIA`, `XPIXSZ/YPIXSZ` |
| 사이트/날씨 | `OBSERVER`, `SITELAT/LONG/ELEV`, `MOONPHAS`, `AMBTEMP`, `HUMIDITY`, `PRESSURE`, `WINDSPED`, `SKYBRGHT`, `SKYFWHM`, `CLUDFRAC`, `RAINRATE` 등 |

### save(save_log=True)
1. `FILENAME_FORMAT`/`FOLDERNAME_FORMAT`의 `$$KEY$$`를 헤더값+합성키로 치환. 합성키: `UTCDATE/LTCDATE`(+`_`/`-` 변형), `UTCDATE12/15`(−12h/−15h 시프트; 기본 폴더명은 UTCDATE15- 사용 → 한 밤이 한 폴더), `UTCTIME/LTCTIME`, `FRAMENUM`(4자리).
2. **`IS_ToO`가 TRUE면 폴더명에 `_ToO` 서픽스** → DataTransferManager의 ToO 고속 전송 경로가 이 서픽스로 감지.
3. `hdu.writeto(IMAGE_PATH/folder/filename, overwrite=False)`. 중복 시 `IMAGE_PATH/dup_<파일명>`(폴더 밖, 버그성).
4. `IMAGE_SAVEHEADER`: `.head` 사이드카(헤더 텍스트).
5. `IMAGE_SAVELOG`: `IMAGE_LOGPATH/<folder>`에 `"<파일명>, <isot>"` append (portalocker 잠금 — 20 unit 동시 쓰기 안전).
- `show()`: ZScale 그레이스케일 표시.

## 6. datatransfer.py — DataTransferManager

관측 데이터 → 데이터센터 서버 전송 관리.

```python
DataTransferManager()   # config TRANSFER_* 사용
```
- `run(key='*/image/20240515', ..., protocol='gridftp'|'hpnscp', from_archive=False)` — 디스패처.
- `gridFTP_transfer(...)`: (옵션) SHA-256 해시 → tar(아카이브 폴더에) → `globus-url-copy -fast -p N -rst-retries R ... sshftp://user@ip:port/...` → (옵션) `move_to_archive_and_cleanup` (원본 → `/data1/obsdata_archive/<7DTxx>/`, tar 삭제).
- `hpnscp_transfer(...)`: `hpnscp -P port src user@ip:dest`.
- `generate_and_save_hash(key)`: unit별(`7DT\d{2}` 정규식) `allfiles.hash` 생성 (SHA-256).
- `tar(...)`: tar 생성 + `TRANSFER_SYNCFOLDER/transfer_history.ascii_fixed_width` 로그 + `.filelist` 기록.
- `start_monitoring(ordinary_file_key='*/image/*', ToO_file_key='*/image/*_ToO', inactivity_period=1800, ...)`: 60초 폴링. hour==12에 일반 데이터 전송; **`*_ToO` 폴더는 inactivity_period 동안 새 파일이 없으면 즉시 전송** (ToO 고속 경로).
- `abort()`: 진행 중 subprocess terminate/kill.

## 7. exception / error

### `utils/exception/exception.py`
**주의**: `utils/exception/__init__.py`는 빈 파일. 실제 코드는 `from tcspy.utils.exception import *` 형태를 쓰는데 이는 exception.py 모듈이 아닌 패키지 임포트 — 실제 정의는 `tcspy.utils.exception.exception`에 있음.

| 그룹 | 예외 |
|---|---|
| Mount | `ParkingFailedException`, `SlewingFailedException`, `TrackingFailedException`, `MountEnableFailedException`, `FindingHomeFailedException` |
| Camera | `ExposureFailedException`, `WarmingFailedException`, `CoolingFailedException` |
| Focuser | `FocusChangeFailedException`, `FocuserEnableFailedException`, `AutofocusFailedException`, `FocusFansFailedException` |
| Filterwheel | `FilterChangeFailedException`, `FilterRegisterException` |
| 제어 흐름 | `AbortionException`, `ConnectionException`, `ActionFailedException` |
| 모드 | `ColormodeRegisterException`, `SpecmodeRegisterException`, `ObsModeRegisterException` |
| 기타 | `DeviceNotReadyException`, `TimeoutException` (Timeout 데코레이터는 이 클래스를 안 씀) |

### `utils/error/error.py`
`FocuserTypeError`, `TelTypeError`(미지원 디바이스 타입), `DBConnectionError`. (`__init__.py` 빈 파일 → `from tcspy.utils.error.error import ...`)

## 8. 스크립트류 (import 금지 — import 시 코드 실행)

- `status_monitor.py` — PyQt5 unit 상태 그리드 GUI 프로토타입 (하드코딩 샘플 데이터, 5초 타이머).
- ~~`ditheringpattern.py`~~ → **2026-08 리팩토링으로 정식 모듈이 됨** (아래 참조). 더 이상 import 시 실행되지 않음.

## 9. ditheringpattern.py (2026-08 리팩토링)

- `generate_dithering_offsets(n_points, offset_arcsec)` → `[(dx, dy), ...]` arcsec 단위 on-sky 오프셋. 5×5 바깥 나선(중심 (0,0) 시작, 25개 고유 위치, ±2×offset 범위), n_points > 25면 중심부터 순환. **SingleObservation 디더링이 사용.**
- `generate_dithering_pattern(ra_center, dec_center, n_points, offset_arcsec)` → 절대 RA/Dec 좌표 배열 (RA는 cos(dec) 보정). 기존 프로토타입 호환용.
- 시각화 데모는 `__main__` 가드 안으로 이동 (임포트 안전).
- `check_focus_offset.py` — FITS 헤더(FOCUSPOS/FILTER)로 필터별 포커스 오프셋 분석. **import 시 input() 프롬프트.**

## 10. helpdesk/ — Obstech helpdesk → Slack 중계 (2026-10 신설)

Obstech helpdesk(`https://helpdesk.obstech.cl`, **osTicket v1.18.2**)의 고객 포털을 로그인해서 읽고, 변경 사항을 Slack에 티켓당 스레드 1개로 올린다. 메일 연동 없음 (생성 시 알림 메일이 오지 않아 포털 폴링으로 결정).

- `HelpdeskPortal` (`helpdeskportal.py`) — 읽기 전용 포털 클라이언트. **tcspy 임포트 없음** (requests + 표준 `html.parser`로 만든 간이 DOM). `login()`(`login.php`에 `__CSRFToken__`/`luser`/`lpasswd` POST), `_get()`(응답이 로그인 페이지[`id="clientLogin"`]면 1회 재로그인), `list_tickets(status='open'|'closed')`(`tickets.php?a=search&status=...` — 포털 목록은 open/closed 중 하나만 보여줌, `<tr id=ticket_id>`), `get_ticket(id)`(`#ticketInfo` + `#ticketThread`의 `thread-entry-<id>`; type은 `message`(사용자)/`response`(staff), 내부 노트는 고객 화면에 안 보임). 로그인 계정이 소유자이거나 참조자(collaborator)인 티켓만 보임.
- `HelpdeskMonitor(mainConfig)` (`helpdeskmonitor.py`) — `check()` 1회: open 목록 전체 + closed 목록 1페이지 중 (신규 또는 직전 open) 티켓만 상세 조회 (열림 여부는 상태 이름이 아니라 어느 목록에서 나왔는지로 판단 — 이 포털의 닫힘 상태 이름은 `Resolved`) → 신규 티켓은 채널 메시지(스레드 부모), 신규 entry·상태 변경은 스레드 답글. 상태 파일(`HELPDESK_STATEPATH`, JSON: ticket_id → `slack_ts`/`entries`/`status`/`is_open`)로 재시작 시 중복 방지, 게시 성공한 entry만 기록. **상태 파일이 없으면 첫 check는 기록만 하고 게시 안 함.** 부모가 없는 기존 티켓은 첫 변경 시 부모 생성. `monitor()` = 무한 루프 (`__main__`).
- 포털 HTML 구조에 의존(스크래핑)하므로 osTicket 업그레이드 시 깨질 수 있음 → 구조를 못 찾으면 RuntimeError로 로그에 남음.


# configuration/ · interfaces/ 참조

← [인덱스로](CODE_REFERENCE.md)

## 1. mainConfig (`configuration/mainconfig.py`)

**거의 모든 TCSpy 클래스의 베이스 클래스.** JSON `.config` 파일들을 찾아 병합해 flat dict `self.config`로 노출.

```python
mainConfig(unitnum: int = None, path: str = '~/TCSpy/')
```

### 동작
1. 글로벌 config: `~/TCSpy/configuration/*.config` 전부 `json.load` 후 병합.
2. `TCSpy.config`가 없으면 기본값으로 생성 후 **RuntimeError** raise (사용자에게 생성 사실 알림).
3. `unitnum` 지정 시: `tel_name = TCSPY_TEL_NAME + '%.2d' % unitnum` (예: `7DT01`). `~/TCSpy/configuration/7DT01/*.config`가 글로벌 위에 덮어씀 (unit 키 우선).

### 주요 속성
| 속성 | 의미 |
|---|---|
| `config` | 병합된 flat dict |
| `unitnum`, `tel_name` | unit 번호, 망원경 이름 |
| `path_config` | `~/TCSpy/configuration` |
| `path_sync` | `~/TCSpy/sync` (공유 런타임 상태 폴더) |
| `path_unit` | `~/TCSpy/configuration/<tel_name>` |

### 메서드
- `update_config(key, value)` — 메모리 갱신 + **해당 키를 포함한 모든 config 파일 재작성**.
- `make_configfile(dict_params, filename, savepath)` — JSON 저장.
- `_initialize_config(ip_address, portnum, reset_autofocusinfo=False)` — 팩토리 리셋: 전체 기본 config 파일 생성, IMAGE_PATH/LOGGER_PATH 디렉토리 생성, autofocus.offset/history 재생성 옵션.
- `__main__` 블록: unit 1–16을 IP `10.0.106.6~21`로 초기화 + unit 21 시뮬레이터(127.0.0.1:32323).

### config 트리 (repo 밖 `~/TCSpy/`에 존재; repo에는 mainconfig.py만 추적됨)
```
~/TCSpy/
  configuration/*.config            # 글로벌
  configuration/<tel>/*.config      # unit별 (mount/camera/filterWheel/focuser/logger/image/switch/autofocus)
  configuration/filtinfo.dict       # {tel_name: [설치 필터 목록]} JSON
  configuration/specmode/<date>/*.specmode   # {tel_name: [filters]} JSON
  configuration/colormode/<date>/*.colormode
  sync/multitelescopes.dict, weatherinfo.dict, alert/, transfer/, rawdata/, log/<tel>/
  credential/gmail/, slack/, googlesheet/
```

## 2. 설정 키 인벤토리 (기본값)

| 파일 | 키 (기본값) |
|---|---|
| TCSpy | `TCSPY_VERSION`('Version 1.0'), `TCSPY_TEL_NAME`('7DT') |
| mount | `MOUNT_DEVICETYPE`('PWI4'|'Alpaca'), `MOUNT_HOSTIP`, `MOUNT_PORTNUM`('8220'), `MOUNT_DEVICENUM`(0), `MOUNT_PARKALT`(40), `MOUNT_PARKAZ`(300), `MOUNT_RMSRA/DEC`(0.15), `MOUNT_CHECKTIME`(0.5), `MOUNT_DIAMETER`(0.5), `MOUNT_APAREA`(0.196), `MOUNT_FOCALLENGTH`(1537.0), `MOUNT_FOCALRATIO`(3), `MOUNT_SETTLETIME`(5), `MOUNT_NAME`(tel_name) |
| camera | `CAMERA_HOSTIP/PORTNUM/DEVICENUM`, `CAMERA_PIXSIZE`(3.76µm), `CAMERA_CHECKTIME`(0.5) |
| filterWheel | `FTWHEEL_HOSTIP/PORTNUM/DEVICENUM/CHECKTIME`, `FTWHEEL_FILTINFOPATH`(configuration/filtinfo.dict) |
| focuser | `FOCUSER_DEVICETYPE`('PWI4'), `FOCUSER_HOSTIP/PORTNUM('8220')/DEVICENUM`, `FOCUSER_MINSTEP`(2000), `FOCUSER_MAXSTEP`(14000), `FOCUSER_CHECKTIME`(0.5) |
| switch | `SWITCH_HOSTIP/PORTNUM/DEVICENUM`, `SWITCH_TYPES`(['MOUNT','FOCUSER','CAMERA']), `SWITCH_KEY_MOUNT`('MOUNT'), `SWITCH_KEY_FOCUSER`('FOCUS'), `SWITCH_KEY_CAMERA`('CAM'), `SWITCH_KEY_FILTERWHEEL`('CAM', SWITCH_TYPES에 없어 미사용) |
| observer | `OBSERVER_LONGITUDE`(-70.7804), `OBSERVER_LATITUDE`(-30.4704), `OBSERVER_ELEVATION`(1580), `OBSERVER_TIMEZONE`('America/Santiago'), `OBSERVER_NAME` |
| image | `FOLDERNAME_FORMAT`("$$UTCDATE15-$$_gain$$GAIN$$"), `FILENAME_FORMAT`("$$TELESCOP$$_$$UTCDATE$$_$$UTCTIME$$_$$OBJECT$$_$$FILTER$$_$$XBINNING$$x$$YBINNING$$_$$EXPTIME$$s_$$FRAMENUM$$"), `IMAGE_PATH`(/data2/obsdata/<tel>/image/), `IMAGE_SAVEHEADER`(True), `IMAGE_FORMAT`('FITS'), `IMAGE_SAVELOG`(True), `IMAGE_LOGPATH`(sync/rawdata/) |
| logger | `LOGGER_SAVE`(True), `LOGGER_LEVEL`('INFO'), `LOGGER_FORMAT`, `LOGGER_PATH`(sync/log/<tel>) |
| transfer | `TRANSFER_SERVER_IP`('210.117.217.71'), `TRANSFER_SERVER_USERNAME`, `TRANSFER_SERVER_PORTNUM`('8022'), `TRANSFER_SOURCE_HOMEDIR`(/data2/obsdata/), `TRANSFER_ARCHIVE_HOMEDIR`(/data1/obsdata_archive/), `TRANSFER_SERVER_HOMEDIR`, `TRANSFER_SYNCFOLDER`(sync/transfer), `TRANSFER_GRIDFTP_NUMPARALLEL`(32), `TRANSFER_GRIPFTP_VERBOSE`(True, **오타 그대로 코드에서 사용**), `TRANSFER_GRIDFTP_RETRIES`(30), `TRANSFER_GRIDFTP_RTINTERVAL`(60) |
| weather | `WEATHER_HOSTIP`('10.0.11.3'), `WEATHER_PORTNUM`(5575), `WEATHER_UPDATETIME`(60), `WEATHER_PATH`, `WEATHER_STATUSPATH`(sync/weatherinfo.dict), 임계값: `WEATHER_HUMIDITY`(85), `WEATHER_RAINRATE`(80), `WEATHER_SKYMAG`(10), `WEATHER_TEMPERATURE_UPPER`(-25)/`LOWER`(40) (**서로 뒤바뀐 듯**), `WEATHER_WINDSPEED`(20) |
| dome | `DOME_HOSTIP/PORTNUM/DEVICENUM/CHECKTIME` (dome 미구현) |
| safetymonitor | `SAFEMONITOR_HOSTIP`('10.0.11.3'), `SAFEMONITOR_PORTNUM`(5565), `SAFEMONITOR_UPDATETIME`(60), `SAFEMONITOR_PATH` |
| target | `TARGET_MINALT`(30), `TARGET_MAXALT`(88), `TARGET_MOONSEP`(40), `TARGET_WEIGHT_ALT`(0.5), `TARGET_WEIGHT_PRIORITY`(0.5) |
| db | `DB_HOSTIP`('localhost'), `DB_ID`('hhchoi'), `DB_PWD`(**소스에 평문**), `DB_NAME`('target'), `DB_HISTORYPATH`(/data2/obsdata/DB_history), `DB_HISTORYFORMAT`('ascii.fixed_width'), `DB_PROGRAMPATH`, `DB_STATUSDIR`(path_sync), `DB_STATUSFORMAT`('ascii') |
| gmail | `GMAIL_USERNAME`('7dt.observation.alert@gmail.com'), `GMAIL_TOKENPATH`(credential/gmail/...) |
| slack | `SLACK_TOKEN`(credential/slack/... 토큰 파일 경로), `SLACK_DEFAULT_CHANNEL`('C07SREPTWFM'), `SLACK_ALERT_CHANNEL`('C07SREPTWFM') |
| helpdesk (2026-10 신설, `helpdesk.config`) | `HELPDESK_URL`('https://helpdesk.obstech.cl/'), `HELPDESK_CREDENTIAL`(credential/helpdesk/helpdesk_account.json — `{"username","password"}`), `HELPDESK_SLACK_CHANNEL`(None=dry run), `HELPDESK_STATEPATH`(sync/helpdesk/helpdesk_state.json), `HELPDESK_CHECKINTERVAL`(300초) |
| googleSheet | `GOOGLESHEET_URL`, `GOOGLESHEET_AUTH`(service account JSON), `GOOGLESHEET_SCOPE`(feeds/drive/spreadsheets) |
| alertbroker | `ALERTBROKER_AUTHUSERS`(승인 이메일 8개), `ALERTBROKER_NORMUSERS`, `ALERTBROKER_ADMINUSERS`, `ALERTBROKER_PATH`(/data2/obsdata/alert_history), `ALERTBROKER_STATUSPATH`(sync/alert) |
| autofocus | `AUTOFOCUS_TOLERANCE_LOWER`(8)/`UPPER`(45), `AUTOFOCUS_OFFSETPATH`(unit/autofocus.offset), `AUTOFOCUS_HISTORYPATH`(unit/autofocus.history), `AUTOFOCUS_FILTINFOPATH` |
| autoflat | `AUTOFLAT_ALTITUDE`(40), `AUTOFLAT_AZIMUTH`(270), `AUTOFLAT_MINCOUNT`(20000), `AUTOFLAT_MAXCOUNT`(40000), `AUTOFLAT_MINEXPTIME`(0.1), `AUTOFLAT_MAXEXPTIME`(10), `AUTOFLAT_WAITDURATION`(10), `AUTOFLAT_FILTERORDER`(42개, 밝은 순 g,r,i,...,u) |
| specmode/colormode | `SPECMODE_FOLDER`(configuration/specmode/20260120/), `COLORMODE_FOLDER`(configuration/colormode/20250313/) |
| startup | `STARTUP_ALT`(30), `STARTUP_AZ`(90), `STARTUP_CCDTEMP`(-10), `STARTUP_CCDTEMP_TOLERANCE`(1) |
| shutdown | `SHUTDOWN_ALT`(30), `SHUTDOWN_AZ`(90), `SHUTDOWN_CCDTEMP`(10), `SHUTDOWN_CCDTEMP_TOLERANCE`(1) |
| nightsession | `NIGHTSESSION_SUNALT_AUTOFLAT`(-8), `_STARTUP`(-6), `_OBSERVATION`(-15), `_SHUTDOWN`(+10) |
| multitelescopes | `MULTITELESCOPES_FILE`(sync/multitelescopes.dict) |
| nightobs | `NIGHTOBS_SAFETYPE`('safetymonitor' \| 'weather') |
| appscheduler | `APPSCHEDULER_AUTOBIAS/AUTODARK/AUTOFLAT`(True), `APPSCHEDULER_SEARCHKEY`(/data2/obsdata/7DT??/image/$$TONIGHT$$/*.fits) |

### autofocus 리셋 파일 형식
- `autofocus.offset`: `{filter: {update_time: '2000-01-01T00:00:00.000', offset: 999, error: 999}}`
- `autofocus.history`: `{filter: {update_time: ..., succeeded: False, focusval: 10000, focuserr: 999}}`

## 3. interfaces/

- `Interface_Runnable` — 추상 `run()`. `Interface_Abortable` — 추상 `abort()`. (deprecated `@abstractclassmethod` 사용; 시그니처 강제 없음 — 서브클래스마다 run() 파라미터 자유롭게 확장)
- `Interface` — 일반 마커 베이스 (`TelescopeStatus`가 상속).
- `__init__.py`는 위 3개만 re-export. `interface_exposure/filterchange/observation/slewAltAz/slewRADec.py`의 결합 마커 클래스들은 **어디서도 사용되지 않음**.

## 4. setup.py

`name='tcspy'`, version 1.0.5, `python_requires>=3.8`, requirements.txt 기반 install_requires. URL이 옛 프로젝트명 `tippy`를 가리킴.

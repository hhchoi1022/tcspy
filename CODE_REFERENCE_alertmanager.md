# utils/alertmanager/ 참조 — ToO 알림 파이프라인

← [인덱스로](CODE_REFERENCE.md)

`__init__.py` export: `Alert`, `AlertBroker`, `AlertMonitor`.

## 1. 전체 흐름

```
소스: Gmail(7dt.observation.alert@gmail.com) | Google Sheet | GW 카탈로그 파일 | astropy Table 파일
      ↓ AlertMonitor.check_new_mail / check_new_sheet   (AlertBroker.read_*)
Alert.decode_mail / decode_gsheet / decode_gwalert / decode_tbl
      ├─ 키 정규화 (required_key_variants)
      ├─ RA/De → 도 변환 ('h' 또는 ':' 포함 시 hourangle로 해석)
      ├─ RIS 타일 매칭 (Tiles.find_overlapping_tiles) — 경계에서 N아크분 이상 안쪽이면
      │    objname/RA/De를 타일로 치환, 원래 이름은 note로 이동
      ├─ 관측 가능성 (MultiTargets.is_ever_observable, sunset_astro~sunrise_astro, 고도 제약만)
      └─ 행별 uuid id 발급 → alert.formatted_data (DB-ready Table)
      ↓ 히스토리 중복 제거: <ALERTBROKER_PATH>/<type>/<타임스탬프|시트명>/alert_rawdata.json 존재 여부
      ↓ 승인 게이트: 메일=ALERTBROKER_AUTHUSERS 발신자만 / 시트=이름이 'ToO'로 끝나야 함 / is_inputted==False
queue.Queue → 알림당 Thread → AlertMonitor.trigger_alert
      ├─ AlertBroker.input_alert: priority 정렬 후 DB_Dynamic.insert → Dynamic 테이블
      ├─ send_alertslack (반환 ts = 이후 스레드 앵커), send_alertmail
      ├─ 15초 폴링 × 최대 48시간: 해당 id의 status=='observed' 대기
      └─ send_observedslack / send_failedslack (스레드 답글; 결과 이메일은 주석 처리로 비활성)
```

**ToO 규칙 요약**
- 알림 경로 기본값: `is_ToO=1`, `is_rapidToO=0` — 즉시 선점은 요청에 명시해야 함 (수용 표현: `is_rapidToO`, `abort observation`, `abort current observation` 등).
- `is_rapidToO=1` → `DB_Dynamic.best_target`이 자체 풀로 최우선 처리 → NightObservation이 현재 관측 중단 후 ToO 수행.
- `obs_starttime` 지정 시 그 시각 경과 후 score 1.0 urgent 타겟이 됨.
- ToO 유효 기간 = **2일** (48시간 모니터링 + 실패 알림 문구).
- 타일 매칭 실패 시 read_mail이 `match_to_tiles=False`로 재시도 → 원 좌표 그대로 진행.

## 2. Alert (`alert.py`, 487줄) — 데이터 모델/디코더

```python
Alert()   # 일반 object (mainConfig 아님)
```

| 속성 | 의미 |
|---|---|
| `rawdata` / `alert_data` | 원본 / 정규화된 dict |
| `alert_type` | 'gmail' \| 'googlesheet' \| 'gw' \| 'table' |
| `alert_sender` | 요청자 이메일 (payload의 requester가 있으면 그걸로 덮음) |
| `formatted_data` | DB-ready astropy Table |
| `is_inputted` / `trigger_time` | DB 삽입 여부/시각 |
| `is_observed` / `observation_time` / `num_observed_targets` | 관측 완료 상태 |
| `is_matched_to_tiles` / `distance_to_tile_boundary` | 타일 스냅 여부 |
| `key` | uuid4 hex |
| `historypath` / `statuspath` | 저장 위치 |

### default_config (모든 알림의 기본값)
```
exptime=100, count=3, obsmode='Spec', filter_='g', specmode='specall',
ntelescope=10, priority=50, weight=1, binning=1, gain=2750,
objtype='Request', is_ToO=1, is_rapidToO=0, cadence=1, id=self.key
```

### required_key_variants — 키 정규화 사전
자유 형식 메일/시트 헤더를 표준 컬럼으로 매핑. 주요 항목:
`objname`(target, object...), `RA`/`De`, `exptime`(exposure, single frame exposure...), `count`(# of images...), `obsmode`, `specmode`, `filter_`, `ntelescope`, `binning`, `gain`, `priority`(rank), `weight`, `objtype`, `note`, `comments`, `is_ToO`, `is_rapidToO`(**abortobservation, abort current observation 포함**), `cadence`, `obs_starttime`, `too_starttime/endtime`, `id`, `is_observable`, `radius`.

### 디코더
- **`decode_mail(mail_dict, match_to_tiles=True, match_tolerance_minutes=3)`** — 첨부 JSON 우선, 실패 시 본문 정규식 파싱(`key : value` / `key = value` / `key value`). is_ToO/is_rapidToO는 문자열 'TRUE'일 때만 1 (**기본값 1(int)은 여기 걸리지 않아 메일에 미명시 시 is_ToO=0이 되는 버그**). specmode 확장자 제거.
- **`decode_gsheet(tbl, ...)`** / **`decode_tbl(tbl, ...)`** — 시트/테이블 헤더 정규화, 미인식 컬럼은 경고 후 폐기. 행별 uuid.
- **`decode_gwalert(tbl)`** — GW/GECKO 타일 카탈로그: `objname='T%05d'`, `priority=rank`, `objtype='GECKO'`, `note=obj`. 타일 매칭 없음(입력이 이미 타일).

## 3. AlertBroker (`alertbroker.py`, 855줄) — I/O 계층

```python
AlertBroker()   # 커넥터(slack/gmail/googlesheet/DB)는 lazy 생성
```

### 읽기 (read_*)
- `read_mail(mailbox='inbox', since_days=1, max_numbers=10, match_to_tiles=False, ...)` → List[Alert]. 메일 저장 → decode(실패 시 타일 매칭 없이 재시도) → historypath = `<ALERTBROKER_PATH>/gmail/<메일 UTC 타임스탬프>` → 신규면 save_alerthistory, 기존이면 load(중복 방지).
- `read_sheet(sheet_name, ...)` → Alert. historypath = `<...>/googlesheet/<시트명>` (시트명이 dedup 키).
- `read_tbl(path, ...)`, `read_gwalert(path)` — 파일 mtime 기반 historypath.

### 히스토리 (dedup 메커니즘)
- `is_history_saved(path)`: `alert_rawdata.json` 존재 여부.
- `save_alerthistory(alert, path)`: `alert_formatted.ascii_fixed_width` + `alert_rawdata.json` + `alert_status.json`(11개 상태 키).
- `load_alerthistory(path)` → Alert 복원 (num_observed_targets는 복원 안 됨).

### DB 삽입
- **`input_alert(alert)`**: formatted_data를 priority 정렬 후 `DB_Dynamic.insert` → `is_inputted=True`, trigger_time 기록. **알림→Dynamic 테이블의 유일한 통로.**

### 알림 발송
| 메서드 | 내용 |
|---|---|
| `send_alertmail(alert, users, cc_users, scheduled_time, attachment)` | HTML 메일 "[7DT ToO Alert] New ToO target(s) are received" — 타겟/노출 정보 박스, 관측 불가 경고, 타일 매칭 안내 |
| `send_observedmail` / `send_failedmail` | 관측 완료/실패 통지 (실패 사유: 저고도/달분리/우선순위; **ToO 유효 2일** 안내) |
| `send_alertslack(alert, scheduled_time)` → `message_ts` | Block-Kit "NEW ToO Alert Request" 게시, **반환 ts가 후속 스레드 앵커** |
| `send_observedslack(alert, message_ts, ...)` / `send_failedslack(...)` | 성공/실패 스레드 답글 |
| `write_gwalert(file_path, write_type='googlesheet', max_size=200)` | 브로커 측: GW 카탈로그를 rank 정렬·상위 200개로 잘라 시트(`<ts>_GECKO`) 또는 파일로 게시 |

## 4. AlertMonitor (`alertmonitor.py`, 309줄) — 상시 데몬

```python
AlertMonitor()
monitor_alert(send_slack=True, send_email=True, check_interval=30, since_days=3,
              max_email_alerts=20, max_sheet_alerts=20, match_to_tiles=True,
              match_tolerance_minutes=5)
```

무한 루프: `check_new_mail` → `check_new_sheet` → 큐의 알림마다 `trigger_alert` Thread 생성(5초 간격) → 완료 스레드 정리 → sleep(check_interval). 예외는 잡아서 출력만 (루프 불사).

- `check_new_mail(...)`: **발신자가 `ALERTBROKER_AUTHUSERS`에 있고 `is_inputted==False`인 알림만** 큐에 넣음 (승인 게이트).
- `check_new_sheet(...)`: 시트 목록에서 'format'/'readme' 포함 제외, **이름이 'ToO'로 끝나는 시트만**, 최신순 max개. (시트는 쓰기 권한 자체가 승인)
- `users` property: `{'authorized', 'normal', 'admin'}` (config ALERTBROKER_*USERS).

### trigger_alert(alert, send_slack, send_email) — 생애주기
1. `input_alert` (DB 삽입) → 상태/히스토리 저장.
2. `send_alertslack` (ts 확보) + `send_alertmail` (승인+일반 사용자, formatted 테이블 첨부).
3. **15초 폴링 × 48시간**: Dynamic에서 해당 id들의 status=='observed' 대기. (**버그: `['id'][0]`만 검사 — 다중 타겟이면 첫 타겟만 확인**)
4. 완료/타임아웃 후 `send_observedslack` 또는 `send_failedslack` (이메일 버전은 주석 처리로 비활성).
5. `update_alertstatus`로 `<ALERTBROKER_STATUSPATH>/<leaf>/`에 상태 재기록.

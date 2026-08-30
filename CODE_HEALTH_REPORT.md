# TCSpy 코드 건강 리포트

> 작성일: 2026-08-06 · 대상: 전체 코드베이스 (HEAD `c991d244d` + 디더링 미커밋 변경분)
> 방법: 3개 독립 감사 (① 디더링 신규 구현 검증, ② action/applications, ③ devices/utils/databases).
> 기존에 알려진 버그 26건을 현재 코드와 대조해 재검증(반박 포함)했고, 신규 40여 건을 발견했습니다.
> **코드는 수정하지 않았습니다.** 모든 라인 번호는 현재 워킹 트리 기준입니다.

---

## 한눈에 보기 (Executive Summary)

운영 중 실제로 밤을 날릴 수 있는 시나리오가 여러 개 확인되었습니다. 가장 위험한 것부터:

| # | 시나리오 | 원인 |
|---|---|---|
| 1 | **abort가 아예 동작하지 않음** — 운영자가 중단 요청해도 관측 계속 | `NightObservation.abort()`의 unpack 버그 |
| 2 | **관측 실패가 DB에 '관측 완료'로 기록** — 타겟이 조용히 영구 손실 | 자식 프로세스 크래시 시 exception 미기록 |
| 3 | **밤 루프가 소리 없이 죽고 셧다운도 안 됨** — 새벽까지 망원경 방치 | `best_target()`의 None 반환 미처리 (2곳) |
| 4 | **대기 중인 abort를 아무 MultiAction이나 지워버림** | `MultiAction.run()`의 `abort_action.clear()` |
| 5 | **PWI4 마운트가 슬루 중에도 항상 'idle'로 보고** | `TelescopeStatus.mount`의 `axis2` 오참조 |
| 6 | **unit 하나만 고장 나도 스케줄러 전체 데드락** | `Startup`의 `pop('7DT06')` KeyError + remove() 불일치 |
| 7 | **흐린 밤이면 아침 셧다운이 스케줄되지 않음** | `get_obsinfo_tonight`의 글롭 무매치 처리 부재 |

**심각도 기준**: 🔴 CRITICAL = 시스템 정지·무음 데이터 오염 / 🟠 HIGH = 특정 조건에서 크래시·행·잘못된 관측 / 🟡 MEDIUM = 기능 저하·잠재 폭탄 / ⚪ LOW = 사소·휴면.

---

## 1. 🔴 CRITICAL — 즉시 조치 권장

### C-1. `NightObservation.abort()`가 100% 실패 — ✅ 수정됨 (2026-08-11)
`applications/nightobservation.py:264`
```python
aborted_action, aborted_observation_status = None   # TypeError: cannot unpack
```
- **트리거**: `abort()` 호출 (수동 중단, 상위 시스템의 중단 요청 등 전부).
- **결과**: `abort_action.set()`(263행)은 실행된 뒤에 터지므로 자식들에 중단 신호는 가지만, 이후의 프로세스 드레인·망원경 반환·DB 정리가 전부 미실행. `is_running`도 영구 True. **abort API가 완전 불능.**

### C-2. 크래시된 관측이 DB에 `'observed'`로 기록됨 (무음 타겟 손실) — ✅ 수정됨 (2026-08-11, 판정 로직: succeeded 병용 + else로 전체 커버. 하위 크래시 경로 4개는 H-2 등에서 별도 수정 예정)
`applications/nightobservation.py:237-247`
- `execute_observation`은 자식 프로세스 종료 후 `shared_memory['exception']`만 봅니다. 자식이 **exception을 기록하지 못하고 죽으면**(무핸들 예외, OOM/SIGKILL) `None` → **이미지 0장인데 'observed' 기록 + CSV 내보내기**. 타겟은 다시는 스케줄되지 않습니다.
- 실제로 도달 가능한 무핸들-예외 경로 4개가 확인됨:
  1. `singleobservation.py:198/201/204` — 상태 로드 실패 시 UnboundLocalError (아래 H-2)
  2. `singleobservation.py:372` — **재개된 관측의 모든 프레임이 이미 완료**된 경우 `observation_trigger['filter_'][0]` → IndexError (디더링/ToO 재개 기능과 직결)
  3. `singleobservation.py:282-283` — 슬루에서 비목록 예외 발생 시 `RuntimeError` re-raise (exception 미기록)
  4. `singleobservation.py:451` + `autofocus.py:136` — autofocus history JSON에 없는 필터명 → KeyError
- **연관**: `exposure.py`의 카메라 상태 fall-through(어느 분기에도 안 걸리면 조용히 None 반환), `all([]) == True`(프레임 0개 트리거 시 succeeded=True)도 같은 'observed' 오기록으로 이어짐.

### C-3. 메인 밤 루프가 None 참조로 사망 → 셧다운 미실행 (2곳) — ✅ 수정됨 (2026-08-11: (a) force_non_ToO 재조회에 None 가드, (b) initialize() no-op 경로가 테이블 반환. `_process` 전체 비상 셧다운 래퍼는 사용자 결정으로 미적용)
- **(a)** `applications/nightobservation.py:446-448` — ToO 30분 스로틀 중 `best_target(force_non_ToO=True)`가 `(None, None)` 반환 시 `best_target["objname"]` → TypeError. **트리거가 일상적**: ToO 직후 + 당장 관측 가능한 일반 타겟 없음.
- **(b)** `utils/databases/DB_dynamic.py:133-134, 197, 203-206` — `best_target`의 재초기화 판단 컬럼(`exptime_tot` 포함)과 `initialize`의 갱신 대상 컬럼(**`exptime_tot` 미포함**)이 불일치. `exptime_tot`만 NULL인 행이 있으면 `initialize()`가 no-op으로 `None`을 반환하고 `target_all['is_rapidToO']`에서 TypeError. `obsmode`/`count` 누락 행이 있으면 영구적으로 이 상태.
- **공통 결과**: `_process`는 무핸들 Thread라 조용히 죽음 → `is_running` 영구 True → `__main__` 무한 스핀, **일출 후 Shutdown(471-473행)도 실행 안 됨**. `run()`은 "cannot be run twice"로 재시작 거부.

### C-4. `MultiAction.run()`이 시작 시 전역 abort를 삭제 — ✅ 수정됨 (2026-08-15, 사용자 직접 수정: multiaction.py:79 주석 처리 + nightobservation의 Event 재생성 3곳 제거, `_abort_observation`/`_abort_ToO` 드레인 후 소유자 측 clear(), `_process`/`_ToOobservation` 진입부 clear(). 부수 효과로 5절의 resume 결함도 해소. ⚠️ 마스터 abort_action은 이제 래칭 — abort 후 재가동/셧다운 시 운영 스크립트에서 명시적 clear() 필요)
`action/multiaction.py:79` — `self.abort_action.clear()`
- `abort_action` Event는 시스템 전역 공유입니다(AppScheduler가 모든 앱에 하나 전달, NightObservation이 악천후 Shutdown에 `self.abort_action` 그대로 전달).
- **결과**: 운영자가 abort를 걸어도 다음에 실행되는 아무 `MultiAction.run()`(Shutdown/Startup의 각 단계 포함)이 **무음으로 지우고 하드웨어를 계속 구동**. Startup 단계 사이에 걸린 abort도 다음 단계가 지움 — 각 단계의 abort 가드가 무력화.

### C-5. `MultiTelescopes.remove()`가 내부 리스트를 안 지움 → KeyError 연쇄 — ✅ 수정됨 (2026-08-17: add()/remove()가 `_devices_list` 동기화 + `pop(name, None)`으로 이중 제거 안전화)
`devices/multitelescopes.py:103-115` — `devices`/`log_dict`만 pop, **`_devices_list`는 그대로**. 그런데 `status`/`filters`/`_dict_logs`는 `_devices_list`를 순회.
- Startup/Shutdown은 실패 unit마다 `remove()`를 호출하고, AppScheduler는 **하나의 MultiTelescopes를 모든 앱이 공유**.
- **결과**: ① `NightObservation.initialize`(92-94행)에서 제거된 unit이 status에는 나타나 `devices[tel_name]` KeyError → **밤 시작 전 사망**. ② 악천후 Shutdown이 unit을 제거한 뒤 `_put_telescope`(510행) KeyError → unit 영구 손실. ③ `register_logfile()`이 제거 unit을 log_dict에 부활시킴. (`add()`의 대칭 버그도 확인 — 추가 unit이 status에 안 보임)

### C-6. `FilterCheck.run()` — 실패 시 AttributeError + 스케줄 작업 재발화 — ✅ 수정됨 (2026-08-17: 비블로킹 구조로 전환[사용자 결정] — run()이 사전 is_running=True 후 스레드 시작, _process 전체 try/finally로 어떤 경로든 is_running 해제+statusfile idle 복구, 결과는 self.result 속성(None=실패), 글롭 필터-한정+빈 결과 가드, M-11(마지막 필터 outlier만 저장/IMAGE_SAVELOG 복원 하드코딩)도 함께 수정. appscheduler run_filtercheck는 result None 체크 후 CancelJob)
`applications/filtercheck.py:41-44` — `self.result`는 happy path 마지막(148행)에서만 할당. `_process`가 예외로 죽으면(실패 경로 5개+) `join()` 후 `return self.result` → **AttributeError**.
- AppScheduler에서 이 예외가 새면 `CancelJob` 미반환 → **다음 날 같은 시각 다시 발화해 어레이를 다시 슬루**시킬 수 있음.
- 부차: 글롭 `'*filtercheck*.fits'`가 필터 미구분(123행, 이전 필터/이전 밤 파일 오픽업), `folder_key`가 노출 전에 계산되어 12h UTC 경계 넘으면 IndexError.

### C-7. `SQLConnector.execute()` — 닫힌 커서 반환 (버전 의존 시한폭탄) — ✅ 수정됨 (2026-08-17: 읽기/쓰기 분리 — `query()` 신설(커서 생존 중 fetchall 후 행 리스트 반환), `execute()`는 True/None만 반환. 읽기 5곳 query()로 전환, 쓰기 경로는 계약 유지. 외부 직접 execute 호출자 없음 확인)
`utils/connector/SQLconnector.py:45-59` — `finally`에서 `cursor.close(); conn.close()` 후 커서 반환. 호출자(`get_data`, `get_colnames` 등)는 닫힌 커서에 `fetchall()`.
- 메인라인 mysql-connector-python에서는 닫힌 buffered cursor의 fetch가 `InterfaceError` 또는 빈 결과 → **커넥터 업그레이드 순간 모든 DB 읽기가 깨지거나, 더 나쁘게는 "타겟 없음"으로 무음 오동작**. 지금 동작한다면 고정된 버전의 우연입니다. 커넥션이 풀로 반환된 뒤 다른 스레드에 재교부되는 동시성 문제도 함께 존재.

---

## 2. 🟠 HIGH — 조건부 크래시 / 행 / 잘못된 관측

### 상태·제어 흐름
| ID | 위치 | 내용 |
|---|---|---|
| H-1 | ~~`devices/telescopestatus.py:89`~~ | ✅ 수정됨 (2026-08-17): `axis2`→`axis1` + is_connected 아래 중첩 + is_slewing을 마지막 체크로(슬루+추적 동시 시 busy 보장, Alpaca 분기도 동일 순서 수정). 파킹(양축 disabled)은 의도적으로 'idle' 유지 — NightObservation.initialize의 IDLE 요구와 호환. **주의: 이후 로그에 'mount is busy' ActionFailedException이 보이면 버그가 아니라 살아난 가드** |
| H-2 | `action/level2/singleobservation.py:176-206` | 상태 로드 3개가 독립 try/except — 실패한 로드의 변수가 unbound인 채 198/201/204행에서 참조 → UnboundLocalError가 ConnectionException 대신 탈출(→ C-2로 연결). `:57` `is_running=True`로 초기화(유일) — 자식이 run() 도달 전 죽으면 영구 True → abort 무한 스핀 |
| H-3 | `action/level1/home.py:102`, `park.py:102` | 실패 핸들러에서 `ActionFailedException(...)` **생성만 하고 raise 안 함** → `result_park` UnboundLocalError. home은 `FindingHomeFailedException`을 아예 안 잡음(같은 크래시, 다른 트리거) |
| H-4 | `action/level1/disconnect.py:69,95,111` | exception 임포트 누락(action/ 전체에서 유일) → abort 경로 NameError |
| H-5 | `action/level1/warm.py:80,89` | disconnected 시 예외를 **return** (호출자는 truthy 객체를 성공으로 오인); 시작 시 `is_running=False` → 슈퍼바이저 폴링 즉시 종료 |
| H-6 | `applications/startup.py:136-142` | `pop('7DT06')` 기본값 없음: 7DT02는 있는데 7DT06이 없으면(사전 Connect 실패 등) KeyError → 스레드 무음 사망 → `is_running` 영구 True → **AppScheduler가 thread_lock을 쥔 채 무한 대기 → 그날 밤 모든 후속 앱 데드락**. `params[:-1]`: 7DT02 부재 시 마지막 unit 팬 무음 미가동 |
| H-7 | `applications/nightobservation.py:208-259` | `execute_observation`에 try/finally 없음 — 중간 예외(statusfile/SQL/portalocker/KeyError) 시 unit이 tel_queue로 영영 안 돌아옴(풀 단조 감소), action_queue 잔류 → 이후 abort 무한루프. **연쇄 기아**: COLOR/SPEC은 전 unit 유휴 요구 → unit 1개만 새도 최상위 COLOR 타겟만 0.5초마다 재선택하며 밤새 아무것도 관측 안 함(로그 없음) |
| H-8 | `applications/appscheduler.py:98-101` | 글롭 무매치 시 `load_collection`이 None → `group_by` AttributeError. **트리거: 흐린 밤(LIGHT 0장)** → 플랫/다크/바이어스/**셧다운 미스케줄** → 새벽 방치 |
| H-9 | `action/level2/autofocus.py:324-348` | 전체 실패 시 예외 없이 None 반환 + `shared_memory['is_running']` True 방치 → 호출자는 포커스 성공으로 오인, `abort()` 무한루프, Manager 프로세스 고정 |
| H-10 | `action/level2/autoflat.py:341-346, 302` | **성공 경로**에서 `is_running` 미해제 → abort() 영구 행. `:302` sky_level 0이면 ZeroDivisionError(캐치 밖) |

### DB·스케줄링 (잘못된 타겟을 조용히 관측)
| ID | 위치 | 내용 |
|---|---|---|
| H-11 | `utils/databases/DB_dynamic.py:594-615` | `_scorer` 인덱스 불일치: score는 non-fixed 부분집합에서 계산, 반환은 전체 테이블 인덱싱 — **고정 시각 타겟이 하나라도 있으면 스코어링된 것과 다른 타겟을 반환**. 예외 없이 조용히 잘못된 대상 관측 |
| H-12 | `utils/databases/DB_survey.py:244-251` | 시각 격자 쿼터 배열이 그룹 간 공유·차감되어 **첫 그룹 이후 쿼터가 ~0** → 이후 그룹 기여 없음; `best_targets`가 누적이 아닌 덮어쓰기 + 이전 그룹의 잔여 `best_target_group`을 vstack — 반환 선택이 알고리즘 의도와 다름. (기존 보고된 NameError는 `n_time_grid=1` 등 특수 조건에서만) |
| H-13 | `utils/databases/DB_dynamic.py:553,606` | `_scorer`가 `Time(settime)`/`.astype(float)`를 무검증 수행 — 'None'/빈 문자열 행 하나로 best_target 전체가 크래시(→ C-3 (b)의 사망 모드). `maxalt`만 astype 누락, `np.clip(0,1,x)` 인자 순서 오류(우연히 유사 동작) |
| H-14 | `utils/connector/SQLconnector.py:110,117` | `insert_rows`가 None을 문자열 `'None'`으로 삽입 (NULL 가드가 `!= ('None' and '') == ''`라 무력) → 하류의 `is None or == ''` 체크가 전부 미스 → `float('None')`/`Time('None')` 크래시의 근원 |
| H-15 | `utils/connector/SQLconnector.py:145,166,104` | SQL 문자열 인터폴레이션 — objname/note에 아포스트로피(`Barnard's Loop`)만 있어도 쿼리 파손 → `except Error`가 삼키고 None 반환 → **무음 쓰기 손실** |
| H-16 | `utils/connector/SQLconnector.py:23-76` | 커넥션 풀 스프롤: SQLConnector마다 pool 16개, `DB()` 하나에 3개 커넥터(≈48 커넥션), NightObservation+AlertBroker+AlertMonitor 각자 생성. `change_db()`는 이전 풀 미폐쇄(+16), `disconnect()`는 `pool=None`만 (재접속 시 AttributeError) |
| H-17 | `utils/databases/DB_program.py:183-213` | `col_to_mjd`가 문자열 날짜에 AttributeError → except pass → NaN → **모든 프로그램 타겟이 유효기간 검사를 무조건 통과**. `target_count` NULL이면 NaN 비교로 "무제한" 의도와 반대(제외됨) |
| H-18 | `utils/alertmanager/alertmonitor.py:168-176` | 다중 타겟 알림에서 `['id'][0]` — **첫 타겟만 관측 확인** 후 성공 통지. 관측 가능 타겟 0개면 IndexError로 알림 스레드 무음 사망(상태 파일·실패 통지 없음) |

### 디바이스 계층
| ID | 위치 | 내용 |
|---|---|---|
| H-19 | `devices/camera/maincamera.py:150-171,228` | `get_status()` 초기화 dict에 `egain` 키 누락(연결 시에만 추가) → 노출과 상태 읽기 사이 연결 끊기면 `mainimage.py:383`에서 KeyError → **촬영된 프레임 손실** |
| H-20 | `utils/image/mainimage.py:142` | `header['IS_ToO'].upper()` — target_info 없는 프레임(캘리브레이션)은 헤더 값이 None → AttributeError → **노출 후 저장 실패** |
| H-21 | `devices/filterwheel/mainfilterwheel.py:107-158` | disconnected면 `get_status()`가 None 반환 → 소비자 `['filter_']`에서 TypeError. 재시도 루프는 `TimeoutException`을 기다리지만 Timeout 데코레이터는 평범한 `Exception`을 던져 **재시도 코드는 dead code** |
| H-22 | `maincamera.py:398`, `mainfilterwheel.py:230`, `mainfocuser_pwi4.py:178,362-371` | abort 체크/타임아웃 없는 무한 대기 루프들 (device_lock 보유 중) — cooler on 대기, 필터 위치 대기, PWI4 focuser connect 대기(마운트 미연결이면 영원히), is_moving 폴링(sleep 없는 타이트 루프) |
| H-23 | `devices/focuser/mainfocuser_pwi4.py:365-380` | `autofocus_start`가 락 해제→`move()`→재획득 패턴 — move()가 raise하면 재획득 스킵 → finally의 release()가 `ValueError: released too many times` → 원 예외 대체 + 락 상태 오염 |
| H-24 | `utils/timeout.py:31-60` | Timeout 초과 시 워커 스레드 미종료(누수) — H-22의 무한 루프와 결합하면 스레드·소켓 무한 축적. 던지는 예외도 `TimeoutException`이 아닌 일반 `Exception`(→ H-21의 원인) |
| H-25 | `devices/telescopestatus.py:31-38` | camera 상태 읽을 때마다 `ThreadPool(1)` 생성 후 미정리 — 20 unit × 상시 폴링으로 스레드 누적 |
| H-26 | `devices/weather/mainweather.py:100-105`, `mainsafetymonitor.py:99-105` | 갱신 루프 전체가 `except: pass` — 일시 오류 한 번에 업데이터 영구 사망, 재시작 없음. 이후 안전 판정 소스가 무음으로 직접 쿼리로 바뀜 |
| H-27 | level3 3파일 (`deepobservation.py:252` 등) | `shared_memory['status'] = multiaction.shared_memory`를 **자식 프로세스 안에서** 저장 — 자식 종료 후 부모가 `_abort_observation`(541행)에서 그 프록시를 읽으면 ConnectionRefusedError/EOFError (abort 내부, 무캐치) |

### 디더링 신규 구현 (이번에 추가한 코드)
| ID | 위치 | 내용 |
|---|---|---|
| H-28 | `devices/mount/mainmount_pwi4.py:638-643` | `offset_radec`의 `is_slewing` 대기 루프에 **abort 체크포인트·타임아웃 없음** (다른 마운트 메서드는 전부 있음). PWI4가 is_slewing=True를 계속 보고하면(축 폴트, 외부 클라이언트 슬루) device_lock 보유 + is_idle cleared 상태로 영구 대기 → 모든 wait_idle() 경로 블로킹 → **악천후 Shutdown까지 막힘**. (PWI4가 완전히 죽으면 status가 None이라 루프 탈출 — '오동작' 케이스가 위험) |
| H-29 | `action/level2/singleobservation.py:534-539` | 최종 `reset_offset()`이 **abort/실패 시 스킵**(raise가 먼저 발생) → 잔여 오프셋(최대 ±2×offset)이 다음 SingleObservation의 post-slew reset 전까지 Shutdown/Park/AutoFlat/filtercheck/수동 PWI4 작업에 전파. try/finally 또는 abort()에서 reset 필요 |

---

> **신규 기능 (2026-08-15)**: Ctrl+C graceful abort — `utils/interrupt.py`의 `InterruptHandler` (SIGINT→플래그 변환, pid 체크로 자식/Manager 면역). `nightobservation.py`·`appscheduler.py` `__main__`에 배선. AppScheduler 러너 8개는 `_wait_action` 헬퍼로 인터럽트 감지→`action.abort()`→Slack 통지. **부수 수정: appscheduler의 `threading.Event`→`multiprocessing.Event`** (기존엔 fork된 자식에 abort 미전파).

## 3. 🟡 MEDIUM — 기능 저하 · 잠재 폭탄

### 동시성·수명주기
- **M-1** `nightobservation.py:448→225`: '스케줄됨' 마킹이 워커 스레드 안 → 메인 루프 0.5s 재쿼리와의 레이스로 **같은 타겟 이중 디스패치** 가능.
- **M-2** Startup/Shutdown/FilterCheck의 `is_running`이 run() 반환 후 `_process`에서 설정 → 슈퍼바이저가 먼저 체크하면 즉시 통과 → **이전 앱이 하드웨어 구동 중인데 다음 앱 시작** (NightObservation은 면제).
- **M-3** `nightobservation.py:76-78`: weather/safetymonitor 스레드가 `daemon=False`인데 종료 조건이 abort_action뿐(C-4가 지움) → 프로세스 정상 종료 불가. NightObservation 재생성마다 한 쌍씩 추가.
- **M-4** Manager 프로세스: 대체로 GC로 회수되나, `aborted_action`을 밤새 보관하는 경로와 H-7 누수 경로는 Manager 프로세스+소켓을 고정.
- **M-5** `_ToOobservation`(nightobservation.py:381-385): 재개가 **동기 호출**이라 ToO 스레드가 각 재개 관측 전체 시간 동안 블로킹; `issubset` 실패 시 로그/DB 갱신 없이 드롭('aborted' 영구); `aborted_action=None` 들여쓰기가 루프 안(의도와 다름).
- **M-6** `multitelescopes.py:47-49` + `:173`: `_register()` 2회 실행 (observer·로거 20개 중복 생성).

### DB·알림
- **M-7** `DB_dynamic.py` 등 9곳: `Time.now()`가 **기본 인자**(임포트 시 고정). `DB_Dynamic.obsnight`도 생성 시 1회 계산 — 장수 프로세스(AlertMonitor)는 며칠 지난 밤 경계로 스코어링.
- **M-8** `alert.py:312-315`: `is_ToO` 기본값 `1`(int)이 `'TRUE'` 문자열 비교에 안 걸림 → **메일에 명시 없으면 is_ToO=0** (기본값 의도와 모순).
- **M-9** `alertmonitor.py:143,198`: `send_slack=False`면 `slack_message_ts` unbound → 알림 스레드 종료 시 UnboundLocalError. `:169,176`: DB 원시값에 `.lower()`/`Time(str)` — None/'None'이면 스레드 사망.
- **M-10** `alert.py:282-304`: default_config에 없는 키(RA/De/objname/note)를 가정 — RA 없는 메일은 KeyError → `read_mail`이 **로그 한 줄 없이 드롭**.
- ~~**M-11** `filtercheck.py`: `self.result`에 마지막 필터 outlier만 저장; IMAGE_SAVELOG 복원 True 하드코딩~~ — ✅ C-6 수정에 포함되어 해결 (2026-08-17).
- **M-12** `autoflat.py:230`: `sky_level_acceleration` 항상 0 (같은 변수 뺄셈) — 노출이 하늘 밝기를 한 프레임 늦게 추적, 아침 플랫 "Sky is too bright" 실패 유발 가능.
- **M-13** `multitargets.py:65-74, 433-441`: `observer` 인자를 무시(내부에서 새로 생성), **달 분리 제약 없음** — 알림의 `is_observable`이 달을 무시하고 판정(메일 문구는 고려한다고 주장).
- **M-14** `mainimage.py:148-158`: 중복 파일이 폴더 밖 `dup_` 경로에 저장(전송 파이프라인이 못 봄); `.head` 사이드카는 폴더 안 경로 사용; **2번째 중복은 overwrite=False로 OSError** → 촬영 후 저장 실패.
- **M-15** `mainimage.py:166`: 20 unit이 같은 저장 로그 파일에 append — portalocker 10초 경합 초과 시 LockException이 save() 밖으로 → 프레임은 디스크에 있는데 노출 실패로 처리.
- **M-16** `os.makedirs` without `exist_ok` 6곳 (alertmonitor/alertbroker/mainimage/GSconnector/gmailconnector) — 동시 생성 레이스에 FileExistsError.
- **M-17** `mainlogger.py:76-77`: 핸들러 존재 시 조기 반환 → **로그 파일명이 프로세스 시작 시각에 고정**(밤 넘어가도 회전 안 됨); 30여 곳의 `register_logfile()`은 사실상 no-op이면서 매번 mainObserver를 새로 생성.
- **M-18** `mainfilterwheel.py:350-353`: Alpaca 위치 `-1`(이동 중)을 `filtnames[-1]`(마지막 필터)로 매핑 → **잘못된 FILTER 헤더**.
- **M-19** `maincamera.py:278-285,431,508,620`: `img_dtype` unbound 가능; `MaxADU`/`cooler_power`/`exptime`이 None일 때 비교·`%d`·`round()`에서 TypeError — 냉각 중단 또는 촬영 프레임 폐기.
- **M-20** `singletarget.py:148,401-414,646-661`: name이 None이면 TypeError; 좌표 없는 타겟의 `is_observable`은 UnboundLocalError; `_format_expinfo`가 길이 불일치 시 사용자의 필터별 값을 **경고 없이 첫 값으로 덮어씀**.
- **M-21** `mainconfig.py:34`: `if self.unitnum:` — **unit 0**은 unit config를 건너뜀(tel_name도 없음).
- **M-22** `appscheduler.py:128`: `alert_slack` — 스크립트 실행 시엔 모듈 전역으로 우연히 해소되나, **임포트해서 쓰면 NameError**.
- **M-23** 디더링: settle이 0.5s 루프+1s 고정 — PWI4는 소형 오프셋에 is_slewing을 안 세울 수 있어 **정착 전 노출로 별 흐름 가능** (slew는 5s settle). `is_stationary`(RMS 기반) 활용 권장.
- **M-24** 디더링: PWI4 `ra_*_arcsec` 규약(on-sky vs 좌표 arcsec) 미검증 — 고적위에서 RA 방향 1/cos(dec) 왜곡 가능. **온스카이 1회 테스트로 확정 필요.** 같은 모듈의 `generate_dithering_pattern`은 cos(dec)를 나누는데 `offset_radec`는 그대로 전달(모듈 내 불일치).
- **M-25** 디더링: post-slew reset이 **모든** PWI4 관측에서 실행 → 운영자/가이더가 PWI4에 외부 설정한 오프셋을 무단 제거 (예외 전파는 없음 — 확인됨).
- **M-26** 디더링: `DITHER_OFFSET_ARCSEC` 컬럼이 없거나 케이스가 다르면 **완전 무음 no-op** (missing-column 경고 로그 없음). 컬럼은 repo 어디에도 자동 생성되지 않으므로 수동 추가 필수.
- **M-27** 디더링 프로세스 비정상 종료(SIGKILL/OOM) 시 device_lock 미해제 + is_idle cleared 영구 — 기존 slew에도 있는 패턴이나 프레임당 2회 락 획득으로 노출 창 증가.

---

## 4. ⚪ LOW — 사소 · 휴면 · 마스킹됨

- `disconnect.py` `__main__`의 인자 누락; `slewAltAz.py`의 디버그 print 잔존; `ChangeFilter` 성공 경로 `shared_memory['is_running']` 미해제.
- level3 `'dicconnected'` 오타(연결 가드 무력 — 실패는 어차피 나중에 ConnectionException으로 표면화); **spec은 체크 블록 전체가 문자열 리터럴**로 주석화. `autofocus_elapsed_time` 이름 불일치(현재 기본값 동일로 마스킹). `all(DictProxy들)` 항상 truthy(MultiAction이 이미 체크해서 마스킹).
- `GSconnector.__repr__`(`_get_sheet_list` 미존재), `gmailconnector.__repr__`/`delete_mail`(미존재 속성/메서드, 후자는 호출자 없음).
- `DB_dynamic._get_target_observable` — 미정의 변수, 호출자 없음(dead code). `alertmonitor`의 `len(x) < 0` dead branch.
- `pwi4_client.py:686-690` str+bytes: **결과는 반박됨** — 자체 try/except 안이라 에러 마스킹 없음, 다만 PWI4 서버측 에러 상세가 항상 소실(진단성 저하). `PWI4Status.__repr__` 빈 응답 시 ValueError.
- `DB_dynamic.py:570` `== None` 원소별 비교 — SQL NULL인 obs_starttime을 놓침('' 체크에만 의존). `:374` 스칼라 vs Column 비교(길이>1이면 ambiguous).
- `gmailconnector.py:166-168` 호출자 리스트 in-place 변형. `SQLconnector` `select_key.split(',')` 공백 미제거.
- 디더링: 음수/0/NaN 값 무음 비활성(로그 없음); 디더 인덱스가 필터별·unit별이라 g,r이 같은 25개 위치 반복 + DEEP/COLOR에서 전 unit 동일 위치(의도라면 무해); visited set float 동등성(현 패턴에선 dead); 배열형 입력 시 `in` 비교 ValueError(현 호출 경로에선 도달 불가).
- `devices/dome`, `devices/rotator` `__init__.py` — 존재하지 않는 모듈 import (임포트하는 곳이 없어 휴면; 단 pytest/pkgutil 등 패키지 워커가 걸림).

---

## 5. 검증 결과 정정·반박된 항목 (기존 보고 대비)

| 항목 | 판정 |
|---|---|
| `singletelescope.register_logfile()` None 반환으로 log가 None | **결함은 맞으나 영향 정정**: 모든 현행 호출 경로가 사용 직전 재호출(내부에서 self.log 재할당)하므로 AttributeError 미도달. 신규 호출자에게만 지뢰 → MEDIUM |
| `pwi4_client` str+bytes로 원 에러 마스킹 | **결과 반박**: 자체 except 안. 상세 정보 소실만 (LOW) |
| `WEATHER_TEMPERATURE_UPPER/LOWER` 뒤바뀜 | **부분 정정**: `mainweather.py:200-201`이 **다시 한 번 뒤바꿔서** 현재 런타임 동작은 정상(-25 < T < 40). ⚠️ **config만 "고치면" 안전 판정이 항상 False가 되어 밤 전체 손실 — 반드시 두 곳 동시 수정** |
| `appscheduler` `alert_slack` NameError | **조건부**: 스크립트 실행 시 모듈 전역으로 해소, 임포트 사용 시만 발화 |
| singleobservation "mount 실패 시 status_camera unbound" | **페어링 정정**: 실패한 로드의 자기 변수가 unbound (메커니즘은 유효) |
| appscheduler vstack 빈 테이블 ValueError 의혹 | **반박**: outer join으로 통과. 단 `imagetyp` 헤더 없으면 KeyError는 별개로 존재 |
| `_ToOobservation` unbound 변수 의혹 | **반박**: 모든 경로에서 바인딩 확인. 유일한 unpack 버그는 `abort()`의 264행 |
| 디더링 resume 경로 | **정상 확인**: `dither_offset_arcsec`이 `action['kwargs']`로 보존, 인덱스=observed로 패턴 연속. 단 resume 자체의 기존 결함(재바인딩된 abort Event를 큐의 액션이 계속 참조 → 재개 즉시 abort)이 별도로 존재 |

---

## 6. 권장 조치 순서 (수정 시)

1. **밤 루프 생존**: C-3 (a)(b) None 가드 + H-13 파싱 가드 → `_process`를 try/except로 감싸 최소한 Shutdown은 보장.
2. **abort 복구**: C-1 unpack 수정, C-4 `abort_action.clear()` 제거, H-28 offset 루프에 abort/타임아웃.
3. **무음 오염 차단**: C-2 — `execute_observation`에서 exception=None이면서 succeeded=False인 경우 'failed' 처리; H-14 'None' 삽입 수정.
4. **unit 손실 방지**: C-5 remove() 동기화, H-6 pop 기본값, H-7 try/finally.
5. **상태 신뢰 회복**: H-1 axis2 수정 (이거 하나로 마운트 busy 판정 전체가 살아남).
6. **디더링 마감**: H-29 try/finally reset, H-28, M-23 settle, M-24 온스카이 확인, M-26 경고 로그.
7. SQL 계층(C-7, H-15, H-16)은 별도 리팩토링 단위로.
8. ⚠️ `WEATHER_TEMPERATURE_*`는 config와 `mainweather._get_constraints`를 **반드시 같은 커밋에서** 수정.

---

*이 리포트는 소스 리딩 기반이며(이 호스트의 파이썬 환경은 numpy 호환 문제로 실행 검증 불가), 라이브러리 버전 의존 항목은 본문에 명시했습니다.*

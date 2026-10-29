# TCSpy 작업 핸드오버 (계정 이전용)

> 작성일: 2026-08-31. Claude 계정 변경 시 이 파일 하나로 이전 작업 맥락을 복원할 수 있도록 작성.
> 새 세션에서 이 파일을 읽으면(또는 "HANDOVER.md 읽고 이어가자"라고 하면) 작업을 그대로 이어갈 수 있다.

---

## 1. 저장 위치 정리 — 무엇이 어디에 있나

| 자산 | 위치 | 계정 이전 시 |
|---|---|---|
| **코드 수정 전체 + 참조 문서 + 버그 리포트** | 이 git 저장소 (커밋 `25ab4562b Dithering/Bugfix`) | ✅ 계정 무관, 완전 보존 |
| 코드 참조 문서 8개 | `CODE_REFERENCE*.md` (저장소 루트) | ✅ 〃 |
| 버그 리포트 + 진행 표시(✅) | `CODE_HEALTH_REPORT.md` (저장소 루트) | ✅ 〃 — **진행 상황의 진실의 원천** |
| Claude 로컬 메모리 3개 파일 | `~/.claude/projects/-lyman-data1-factory-hhchoi-code-tcspy/memory/` | ⚠️ 로컬 디스크(클라우드 아님). 같은 머신·같은 프로젝트 경로면 유지될 가능성이 높지만, 보험으로 내용을 이 파일 §4에 복제해둠 |
| 대화 세션 기록 | Claude 계정 클라우드 | ❌ 이전 안 됨 — 대신 이 파일이 요약 역할 |

---

## 2. 프로젝트 상태 요약

**TCSpy**: 7DT 다중 망원경 어레이 제어 시스템 (ASCOM Alpaca + PWI4 HTTP).
전체 코드 정독 → 참조 문서화 → 디더링 구현 → 전체 감사 리포트 작성 → 리포트 항목 순차 수정 진행 중.

### 완료된 작업
1. **참조 문서** (`CODE_REFERENCE.md` = 인덱스 + 모듈별 7개): 아키텍처/클래스/설정 키/알려진 버그. 코드 재정독 대신 이걸 먼저 볼 것. 코드 수정 시 해당 문서도 갱신하는 규약.
2. **디더링 구현**: DB `Dynamic` 테이블의 `DITHER_OFFSET_ARCSEC` 컬럼(수동 추가 필요, NULL=비활성) → `NightObservation.dispatch_observation` → level3 → `SingleObservation`(프레임마다 5×5 소용돌이 패턴, 인덱스=observed로 재개 연속성) → `mainMount_pwi4.offset_radec/reset_offset`(PWI4 `mount_offset` API). 온스카이 미검증 항목: PWI4 ra 오프셋 단위(cos dec 문제, 리포트 M-24).
3. **Ctrl+C graceful abort**: `utils/interrupt.py`의 `InterruptHandler` — SIGINT를 플래그로 변환, pid 체크로 fork된 자식/Manager 면역. `nightobservation.py`·`appscheduler.py` `__main__` 배선. appscheduler 러너 8개는 `_wait_action` 헬퍼 경유. appscheduler의 Event를 threading→multiprocessing으로 교체.
4. **버그 수정 완료분** (상세는 `CODE_HEALTH_REPORT.md`의 ✅ 표시):
   - C-1 `NightObservation.abort()` unpack TypeError
   - C-2 크래시 관측이 'observed'로 기록 → succeeded 병용 판정 + else 전체 커버
   - C-3 밤 루프 None 참조 2곳 (force_non_ToO 재조회 가드, initialize no-op 테이블 반환) — `_process` 비상 셧다운 래퍼는 **사용자 결정으로 미적용**
   - C-4 `MultiAction.run()`의 `abort_action.clear()` 제거 (사용자 직접 수정) — Event는 `__init__`에서 1회 생성, 이후 소유자가 set/clear만. **마스터 abort는 래칭: abort 후 재가동 시 운영 스크립트에서 명시적 clear 필요**
   - C-5 `MultiTelescopes.add()/remove()` `_devices_list` 동기화 + `pop(name, None)`
   - C-6 FilterCheck **비블로킹 전환**(사용자 결정): run()에서 사전 `is_running=True`, `_process` 전체 try/finally, 결과는 `self.result`(None=실패), 글롭 필터-한정. M-11 포함 해결
   - C-7 SQLConnector 읽기/쓰기 분리: `query()` 신설(커서 생존 중 fetchall), `execute()`는 True/None. 외부 직접 호출자 없음 확인
   - H-1 `telescopestatus.py` PWI4 `axis2`→`axis1` + `is_slewing` 마지막 체크(슬루+추적 동시=busy, Alpaca 동일) + is_connected 중첩. 파킹은 의도적 'idle' 유지. **이후 'mount is busy' 로그는 살아난 가드이지 새 버그 아님**

### 다음 차례: **H-2**
`action/level2/singleobservation.py:176-206` — 디바이스 상태 로드 3개(mount/camera/filterwheel)가 독립 try/except라 실패한 로드의 변수가 unbound인 채 참조됨 → UnboundLocalError가 ConnectionException 대신 탈출 (C-2 크래시 경로 4개 중 1번의 근원). 같은 파일 `:57`의 `shared_memory['is_running'] = True` 초기화(전체 액션 중 유일)도 함께 — 자식이 run() 도달 전 죽으면 영구 True → abort 무한 스핀.
이후 남은 항목: H-3~H-29, MEDIUM/LOW (리포트 참조).

---

## 3. 작업 방식 (합의된 규약)

항목마다: ① `git diff`로 현재 상태 확인(사용자가 직접 수정하는 경우 있음) → ② 실제 코드 읽으며 상세 설명 → ③ 사용자 확인/결정 대기 → ④ 승인분만 최소 diff로 수정 → ⑤ `py_compile` 검증 + 가능하면 로직 단독 테스트 + 생성된 `.pyc` 삭제 → ⑥ `CODE_HEALTH_REPORT.md`에 ✅ 표시 (필요시 CODE_REFERENCE도 갱신).

환경 참고: 이 호스트의 기본 python 환경은 numpy 2.x/astropy 비호환으로 tcspy 임포트 실행 불가(문법·단독 로직 검증만 가능), mysql-connector 미설치(SQL 계층은 소스 리딩 검증만).

---

## 4. 로컬 메모리 파일 내용 복제 (보험)

새 계정에서 메모리가 비어 있으면 아래 3개 파일을 `~/.claude/projects/-lyman-data1-factory-hhchoi-code-tcspy/memory/`에 재생성하면 된다.

### MEMORY.md
```markdown
# MEMORY

- [TCSpy 코드 참조 문서](code-reference-docs.md) — 저장소 루트 CODE_REFERENCE*.md 8개 파일; 코드 재정독 대신 먼저 참조
- [버그 수정 진행 상황](bugfix-progress.md) — CODE_HEALTH_REPORT 항목별 수정 중, CRITICAL 전체(C-1~C-7)+H-1 완료, 다음은 H-2; 작업 방식(설명→확인→수정) 포함
```

### code-reference-docs.md
```markdown
---
name: code-reference-docs
description: TCSpy 저장소 루트에 전체 코드 참조 문서(CODE_REFERENCE*.md) 존재 — 코드 재정독 대신 이걸 먼저 볼 것
metadata:
  type: project
---

TCSpy 저장소 루트에 2026-08-06 전체 코드 정독으로 작성한 한국어 참조 문서 세트가 있다. 코드 구조/클래스/메서드/설정 키/알려진 버그를 찾을 때 전체 코드를 다시 읽지 말고 이 문서들을 먼저 참조할 것:

- `CODE_REFERENCE.md` — 인덱스, 아키텍처 개요, 알려진 버그 총정리, 파일 인덱스
- `CODE_REFERENCE_configuration.md` — mainConfig, 전체 설정 키 인벤토리, interfaces
- `CODE_REFERENCE_devices.md` — SingleTelescope/MultiTelescopes/TelescopeStatus/pwi4_client
- `CODE_REFERENCE_action.md` — 액션 공통 패턴, MultiAction, level1/2/3
- `CODE_REFERENCE_applications.md` — NightObservation, AppScheduler, Startup/Shutdown 등
- `CODE_REFERENCE_utils.md` — NightSession, connector, logger, mainImage, datatransfer, 예외 목록
- `CODE_REFERENCE_databases.md` — 타겟 DB 스키마, best_target 스코어링, SingleTarget/MultiTargets
- `CODE_REFERENCE_alertmanager.md` — ToO 알림 파이프라인

**How to apply:** 코드 질문/수정 요청 시 해당 모듈 문서를 먼저 읽고, 필요한 파일만 골라 읽는다. 코드 수정 후에는 관련 문서 섹션도 함께 갱신한다. 사용자는 문서를 저장소 루트, 한국어, 모듈별 분할 구성으로 원했다.
```

### bugfix-progress.md
```markdown
---
name: bugfix-progress
description: CODE_HEALTH_REPORT.md 항목별 수정 진행 상황과 작업 방식 — 다음 차례는 H-2
metadata:
  type: project
---

[[code-reference-docs]]의 `CODE_HEALTH_REPORT.md` 항목을 순서대로 수정하는 작업이 진행 중이다 (각 항목의 ✅/🔍 표시가 진실의 원천 — 리포트 파일을 먼저 확인할 것).

2026-08-17 기준: **CRITICAL 7건(C-1~C-7) 전부 완료 + H-1 완료.** 상세는 저장소 루트 HANDOVER.md §2 참조.

**다음 차례: H-2** (singleobservation.py:176-206 상태 로드 3개 독립 try/except → 실패 로드의 자기 변수 unbound → UnboundLocalError 탈출; __init__의 shared_memory['is_running']=True 초기화 → 자식이 run 도달 전 죽으면 abort 무한 스핀). C-2의 크래시→'observed' 경로 4개 중 첫 번째의 근원.

**Why:** 세션이 바뀌어도 어디까지 했는지, 어떤 방식으로 일하는지 재확인 없이 이어가기 위해.

**How to apply:** 작업 방식 = ①git diff로 현재 상태 확인 → ②실제 코드 확인하며 상세 설명 → ③사용자 확인/결정 대기 → ④승인분만 수정(최소 diff) → ⑤py_compile 검증+.pyc 삭제 → ⑥리포트에 ✅ 표시. 사용자가 직접 수정하는 항목도 있음. mysql-connector 미설치라 SQL 계층은 실행 검증 불가.
```

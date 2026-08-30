# utils/databases/ · utils/target/ 참조 — 타겟 DB와 스케줄링

← [인덱스로](CODE_REFERENCE.md)

`databases/__init__.py` export: `DB_Dynamic`, `DB_Survey`, `DB_Program`, `DB` (Tiles는 주석 처리 — `from tcspy.utils.databases.tiles import Tiles`로 직접 임포트).

## 1. DB (`mainDB.py`)

```python
DB(utctime=Time.now())
# .Dynamic = DB_Dynamic(tbl_name='Dynamic')   ← 오늘 밤 스케줄링 테이블
# .RIS     = DB_Survey(tbl_name='RIS')        ← 서베이 타일
# .IMS     = DB_Survey(tbl_name='IMS')        ← IMSNG
```
생성 시 3개 모두 즉시 생성 (SQL 연결 3개 + 밤 에페메리스 계산).

## 2. DB_Dynamic (`DB_dynamic.py`, 727줄) — "지금 뭘 관측할까"

```python
DB_Dynamic(utctime=Time.now(), tbl_name='Dynamic')
```
속성: `observer`(mainObserver), `sql`(SQLConnector), `constraints`(minalt/maxalt/moon_separation), `obsinfo`(달/태양 위치 등), `obsnight`(NightSession).

### 주요 메서드

**`initialize(initialize_all=False)`** — 누락된 계산 컬럼 채움:
- 빈 `id`에 uuid 발급 → `risetime`(TARGET_MINALT horizon, previous), `settime`(next), `transittime`/`maxalt`/`besttime`(자오선 통과 기반; 박명 창 밖이면 박명 경계 중 높은 쪽), `moonsep` 계산 → SingleTarget으로 `exptime_tot` 등 노출 정보 계산 → 행별 `update_row`. 실패 행은 `status='error'`.
- `initialize_all=False`면 누락 행만 (메인 루프에서 매회 호출 — 신규 타겟 반영 경로).

**`best_target(utctime, force_non_ToO=False)` → (Row|None, score|None)** — 스케줄러 진입점:
1. `is_rapidToO==1` 행이 있으면 그 풀만 먼저 `_scorer()` — **rapid ToO가 항상 선점** (`force_non_ToO=True`로 우회 가능).
2. 아니면 `priority` 컬럼으로 group_by(오름차순) → **낮은 priority 그룹부터** 순서대로 `_scorer()`, 첫 번째로 타겟이 나오는 그룹 채택.

**`_scorer(utctime, target_tbl)`** — 스코어링 핵심:
- `status=='unscheduled'`만 대상.
- **고정 시각 타겟**: `obs_starttime`이 이미 지났고 오늘 관측 창 안이면 "urgent" — 제약 통과 시 가장 이른 것을 **score=1.0으로 즉시 반환** (하드 오버라이드).
- 하드 제약 (곱셈으로 0 처리): `moonsep > TARGET_MOONSEP(40)`, `alt > TARGET_MINALT(30)`, `alt < TARGET_MAXALT(88)`. ("지기 전에 끝낼 수 있나"와 "밤인가" 제약은 **주석 처리로 비활성**.)
- 연속 스코어: `0.5×clip(alt/maxalt,0,1) + 0.5×(weight/max weight)` (가중치 = TARGET_WEIGHT_ALT/PRIORITY). alt/maxalt라서 자오선 근처 타겟 선호.
- **버그**: 고정 시각 타겟이 존재하면 `idx_best`가 non-fixed 부분집합 인덱스인데 전체 테이블에 적용 → 엉뚱한 행 반환 가능.

**타겟 유입 메서드**: `from_RIS(size=300, ...)` (DB_Survey.select_best_targets 결과 삽입), `from_IMS()` (IMS 전체 삽입), `from_Program(...)`, `from_GSheet(sheet_name, match_to_tiles=True)` (구글시트 직접 유입 + RIS 타일 스냅).

**피드백 메서드**: `update_7DS_obscount(remove, reset_status, ...)` — status=='observed' 행을 RIS/IMS/WFS 테이블에 `obs_count+1`, `last_obsdate` 기록. `update_program_obscount(...)` — 비서베이 타겟을 Program 테이블에 기록/생성 (`obs_endtime`→`last_obstime`).

**기타**: `insert(Table)`, `update_target(update_values, update_keys, id_value, id_key)`, `clear(clear_only_7ds, clear_only_observed)`, `data` property, `export_to_csv(save_type='status'|'history')` (status→`DB_STATUSDIR/DB_Dynamic.ascii`, history→`DB_HISTORYPATH/Dynamic_YYYYMMDD`).

`__main__` = 야간 준비 레시피: obscount 갱신 → 7DS 행 정리 → from_IMS → from_RIS(150) → from_Program.

## 3. DB_Survey (`DB_survey.py`) — RIS/IMS/WFS 타일 테이블

```python
DB_Survey(tbl_name='RIS')   # change_table()로 RIS/IMS/WFS 전환
```

**`initialize(...)`** — `risedate/bestdate/setdate`(연 단위, MultiTargets.rts_date) + 노출 정보 계산.

**`select_best_targets(utcdate, size=300, observable_minimum_hour=2, n_time_grid=10, galactic_latitude_limit=15, declination_upper_limit=0, declination_lower_limit=-90)`** — 그날 밤 타일 선정:
1. 하늘 컷: `|은위| > 15°`, `-90 < dec < 0`.
2. astroplan `observability_table`(30분 격자, 관측 창)에서 관측 가능 시간 비율 > `observable_minimum_hour/observable_hour`, `risedate != 'Never'`.
3. **`obs_count`로 그룹핑 — 덜 관측된 타일 우선.**
4. 그룹 내 dec 내림차순, `maxalt ≈ 90-|위도-dec|` 근사.
5. 일몰→일출 `n_time_grid` 시각 격자에 쿼터(size//n) 배분; 각 시각에 `alt/maxalt > 0.7` & alt>MINALT & moonsep>MOONSEP인 타일 채택.
6. 상위 `size`개 반환.

기타: `to_Dynamic(tbl)`(Dynamic에 삽입), `update_target(...)`, `visualize(...)`(Mollweide 타일 맵).

## 4. DB_Program (`DB_program.py`) — 장기 프로그램 테이블

`DB_Survey`와 유사 구조. `_set_constrints()`는 **고도 제약만** (달 분리 주석 처리).

**`select_best_targets(utcdate, observable_minimum_hour=1)`** — 관측성 비율 + 3중 AND 필터:
1. **유효 기간**: `obs_startdate ≤ now ≤ obs_enddate` (NULL이면 무제약).
2. **횟수**: `obs_count < target_count`.
3. **케이던스**: `cadence ≤ 0`이거나 미관측이면 통과; 아니면 `now - last_obstime ≥ cadence`(일).

크기 제한/시각 격자 배분 없음.

## 5. 테이블 스키마 (코드에서 역산; MySQL에 직접 생성됨)

접속: `SQLConnector(host=DB_HOSTIP, user=DB_ID, pwd=DB_PWD, db=DB_NAME='target')`.

### Dynamic (구명: Daily)
| 컬럼 | 역할 |
|---|---|
| `idx` | MySQL auto-increment (삽입 시 제거됨) |
| `id` | uuid4 hex 논리 키 (`set_data_id`로 자동 발급) |
| `objname` | 타겟/타일명 (예: T08415, GRB241127A) — 보조 키 |
| `RA`, `De` | 도 단위 |
| `objtype` | RIS/IMS/WFS/GECKO/Request/... (서베이 vs 프로그램 구분) |
| `note` | **요청이 타일에 매칭되면 원래 이름이 여기로 이동** |
| `comment`(s) | 자유 텍스트 |
| `exptime`, `count`, `filter_`, `binning` | 콤마 구분 다필터 허용 |
| `gain` | 기본 2750 |
| `obsmode` | Spec/Deep/Color/Search/Single |
| `specmode`/`colormode` | 모드 파일명 (확장자 없이) |
| `ntelescope` | 사용 unit 수 |
| `exptime_tot` | Σ(exptime×count) 계산값 |
| `priority` | **그룹/티어 인덱스 — 오름차순으로 우선 서비스** |
| `weight` | 그룹 내 연속 스코어 가중치 |
| `is_ToO`, `is_rapidToO` | 0/1 — **rapidToO=1이면 전체 선점** |
| `status` | unscheduled → scheduled → observed/aborted/failed/unobservable (초기화 실패 시 error) |
| `obs_starttime` | 사전 설정 시 = 요청 관측 시각(urgent 경로); 아니면 관측 시작 시 기록 |
| `obs_endtime` | 관측 종료 시 기록 |
| `risetime`,`transittime`,`settime`,`besttime`,`maxalt`,`moonsep` | initialize 계산값 |
| `is_observable`, `cadence` | 알림 경로에서 기록 |
| `DITHER_OFFSET_ARCSEC` | (2026-08 추가) 디더링 간격(arcsec). 유효한 값이면 NightObservation이 관측에 스파이럴 디더링 적용; NULL/빈값이면 디더링 없음 |

### RIS/IMS/WFS
Dynamic의 타겟/노출 컬럼 + `obs_count`(관측 횟수 — 공평성 그룹핑 기준), `last_obsdate`, `risedate/bestdate/setdate`('Always'/'Never' 특수값).

### Program
Dynamic 공통 컬럼 + `obs_count`, `target_count`(요청 총 횟수), `cadence`(최소 간격 일), `last_obstime`, `obs_startdate`/`obs_enddate`(유효 기간).

## 6. Tiles (`tiles.py`) — 타일 기하 엔진

```python
Tiles(tile_path=None)   # 기본: databases/tileinfo/7-DT/final_tiles.txt
```
타일 파일 스키마: `id ra dec ra1 dec1 ra2 dec2 ra3 dec3 ra4 dec4` (id는 T00000 형식, 중심+4모서리 도 단위).

**`find_overlapping_tiles(list_ra, list_dec, list_aperture=0, ..., match_tolerance_minutes=4, fraction_overlap_lower=0.2)` → (Table, matched_indices, fig_path)**
- aperture=0: 점 매칭 — 점이 가장 깊이 들어간 타일 1개 (`_find_innermost_tile`).
- aperture>0: 구면 원(`make_sky_circle_polygon`, 고적위 정확) vs 타일 폴리곤 겹침 비율 > 기준인 타일들.
- 결과 컬럼 추가: `matched_idx`, `distance_to_boundary`(도), `overlapped_area`, `is_within_boundary`(경계에서 `match_tolerance_minutes` 아크분 이상 안쪽인지).
- RA=0/360 랩어라운드 처리 (`_split_wrapping_polygon`).
- `visualize_tiles(...)`: 매칭 진단 그림 저장.

기타 파일: `load_IMSNG.py`(IMSNG 갤럭시 목록 로더), `filter_overlapping_tiles.py`(타 망원경 타일과 교차 분석 독립 유틸), `load_7DT_tile.py`(**레거시 스크립트 — 임포트 경로/메서드명 모두 현재 코드와 불일치, 사용 금지**), `tileinfo/`(7-DT/CBNUO/KCT/KMTNet/RASA36 타일 데이터).

## 7. utils/target/ — SingleTarget / MultiTargets

### SingleTarget (`singletarget.py`, 719줄)

```python
SingleTarget(observer, ra=None, dec=None, alt=None, az=None, name='', objtype=None,
             id_=None, note=None, comment=None, is_ToO=False, is_rapidToO=False,
             exptime=None, count=None, obsmode=None, filter_=None,
             specmode=None, colormode=None, ntelescope=1, gain=2750, binning=1)
```
- 이름 정리: 공백 제거, `/`→`-`, `_`→`-` (GRB 241127A → GRB241127A).
- coordtype: ra/dec → 'radec', alt/az → 'altaz' (radec이 우선).
- **`exposure_info`** (property): exptime/count/filter_/binning 정규화(콤마 분리, 길이 불일치 시 첫 원소 브로드캐스트), `exptime_tot=Σ(exptime×count)`, specmode/colormode면 `SPECMODE_FOLDER/<name>.specmode`(JSON {tel: [filters]}) 로드 → `specmode_filter`/`colormode_filter`. 파일 없으면 `SpecmodeRegisterException`/`ColormodeRegisterException`.
- **`target_info`** (property): 좌표(도/시각 문자열), hourangle, `is_observable`, `moonsep`, 메타 필드 전부.
- 메서드: `is_observable(utctime)` (radec: astroplan is_event_observable [고도+달분리]; altaz: MINALT<alt<MAXALT), `altaz()`, `risetime/settime(mode, horizon=30)`, `meridiantime()`, `hourangle()`, `moon_sep()`, `staralt()`(고도 플롯).
- 제약: `AltitudeConstraint(MINALT, MAXALT, boolean=True)` + `MoonSeparationConstraint(MOONSEP)`.

### MultiTargets (`multitargets.py`)

```python
MultiTargets(targets_ra, targets_dec, targets_name=None, **kwargs)
# 주의: observer 파라미터는 받지 않음(**kwargs로 버려짐) — 내부에서 mainObserver() 새로 생성
```
- 벡터 SkyCoord 하나를 FixedTarget으로 래핑.
- **제약은 고도만** (달 분리 없음 — 호출자가 별도 적용).
- `rts_date(year, time_grid_resolution=3)`: 1년치 일별 관측성 → (risedate, bestdate, setdate); 전 기간 가능→'Always', 불가→'Never'. RIS/IMS/Program의 연 단위 날짜 컬럼 생성.
- `is_ever_observable(start, end, resolution=1h)`, `is_always_observable`, `is_event_observable`, `altaz`, `risetime/settime/meridiantime(n_grid_points=50)`, `hourangle`, `moon_sep`.

## 8. 스케줄링 우선순위 사다리 (종합)

1. **rapid ToO** (`is_rapidToO==1`) — 자체 풀로 최우선 스코어링. NightObservation이 30분 스로틀로 `_ToOobservation()` 진입.
2. **urgent 고정 시각 타겟** — `obs_starttime` 경과 + 오늘 창 내 → score 1.0 즉시 반환.
3. **priority 그룹 오름차순** — 그룹 1에 관측 가능 타겟이 있는 한 그룹 2는 절대 안 봄.
4. 그룹 내 연속 스코어: `0.5×(alt/maxalt) + 0.5×(weight/max weight)`.

하드 제약: moonsep>40°, 30°<alt<88° (범위 밖 = 스코어 0).

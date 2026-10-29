#!/usr/bin/env python3
# %%
import json
from pathlib import Path


missed_OBSERVATION_PATH = Path('/home/kds/tile_stats_incomplete_mb.csv')
COVERABLE_OBSERVATION_PATH = Path('/home/kds/tile_stats_incomplete_mb_coverable.csv')
SELECTED_FILTERSET_OBSERVATION_PATH = Path(
    '/home/kds/tile_stats_incomplete_mb_nmissed_gt5_selected_filterset.csv'
)
SELECTED_FILTERSET_OBSERVATION_ASCII_PATH = Path(
    '/home/kds/tile_stats_incomplete_mb_nmissed_gt5_selected_filterset.ascii_fixed_width'
)
SELECTED_FILTERSET_PATH = Path(
    '/home/kds/TCSpy/configuration/specmode/20260523/missed_filters_1.specmode'
)
MAX_FILTERS_PER_TELESCOPE = 2
MIN_missed_FILTERS = 3

SELECTED_FILTERSET = {
    '7DT01': ['g', 'g'],
    '7DT02': ['m425', 'm675'],
    '7DT03': ['g', 'g'],
    '7DT04': ['m475', 'm725'],
    '7DT05': ['m500', 'm750'],
    '7DT06': ['g', 'g'],
    '7DT07': ['m550', 'm800'],
    '7DT08': ['m575', 'm825'],
    '7DT09': ['g', 'g'],
    '7DT10': ['g', 'g'],
    '7DT11': ['m650', 'm500'],
    '7DT12': ['m675', 'm525'],
    '7DT13': ['m700', 'm850'],
    '7DT14': ['m725', 'm875'],
    '7DT15': ['m450', 'm600'],
    '7DT16': ['m775', 'm625'],
}
#%%

def parse_missed_filters(missed_filters_str):
    if missed_filters_str is None:
        return []

    text = str(missed_filters_str).strip()
    if text in ['', 'None', '--']:
        return []

    filters = []
    for filtname in text.split(','):
        filtname = filtname.strip()
        if filtname and filtname not in filters:
            filters.append(filtname)
    return filters


def get_available_filtersets(multitelescopes):
    filtersets = dict()
    for tel_name, telescope in multitelescopes.devices.items():
        filtnames = getattr(telescope.filterwheel, 'filtnames', None)
        filtersets[tel_name] = set(filtnames or [])
    return filtersets


def assign_missed_filters(missed_filters, filtersets, max_filters_per_telescope=2):
    slots = []
    for tel_name in sorted(filtersets.keys()):
        slots.extend([(tel_name, slot_idx) for slot_idx in range(max_filters_per_telescope)])

    candidates_by_filter = dict()
    for filtname in missed_filters:
        candidates = []
        for slot in slots:
            tel_name, _ = slot
            if filtname in filtersets[tel_name]:
                candidates.append(slot)
        candidates_by_filter[filtname] = candidates

    unavailable_filters = [
        filtname for filtname, candidates in candidates_by_filter.items()
        if len(candidates) == 0
    ]
    if unavailable_filters:
        return dict(
            is_coverable=False,
            selected_filters_by_tel=dict(),
            uncovered_filters=unavailable_filters,
        )

    slot_to_filter = dict()

    def assign_to_slot(filtname, visited_slots):
        for slot in candidates_by_filter[filtname]:
            if slot in visited_slots:
                continue
            visited_slots.add(slot)

            if slot not in slot_to_filter:
                slot_to_filter[slot] = filtname
                return True

            displaced_filter = slot_to_filter[slot]
            if assign_to_slot(displaced_filter, visited_slots):
                slot_to_filter[slot] = filtname
                return True

        return False

    filters_by_fewest_candidates = sorted(
        missed_filters,
        key=lambda filtname: (len(candidates_by_filter[filtname]), filtname),
    )
    for filtname in filters_by_fewest_candidates:
        if not assign_to_slot(filtname, set()):
            assigned_filters = set(slot_to_filter.values())
            return dict(
                is_coverable=False,
                selected_filters_by_tel=_format_selected_filters(slot_to_filter),
                uncovered_filters=[
                    filter_ for filter_ in missed_filters
                    if filter_ not in assigned_filters
                ],
            )

    return dict(
        is_coverable=True,
        selected_filters_by_tel=_format_selected_filters(slot_to_filter),
        uncovered_filters=[],
    )


def _format_selected_filters(slot_to_filter):
    selected_filters_by_tel = dict()
    for slot, filtname in sorted(slot_to_filter.items()):
        tel_name, _ = slot
        selected_filters_by_tel.setdefault(tel_name, []).append(filtname)
    return selected_filters_by_tel


def check_missed_filter_coverage(missed_observation_tbl, filtersets):
    coverage_results = []
    for row in missed_observation_tbl:
        missed_filters = parse_missed_filters(row['missing_filters_str'])
        coverage_results.append(
            assign_missed_filters(
                missed_filters=missed_filters,
                filtersets=filtersets,
                max_filters_per_telescope=MAX_FILTERS_PER_TELESCOPE,
            )
        )

    checked_tbl = missed_observation_tbl.copy()
    checked_tbl['is_coverable_by_current_filters'] = [
        result['is_coverable'] for result in coverage_results
    ]
    checked_tbl['selected_filters_by_tel'] = [
        json.dumps(result['selected_filters_by_tel'], sort_keys=True)
        for result in coverage_results
    ]
    checked_tbl['uncovered_filters_str'] = [
        ','.join(result['uncovered_filters']) for result in coverage_results
    ]
    return checked_tbl


def select_fully_coverable_targets(checked_missed_observation_tbl):
    return checked_missed_observation_tbl[
        checked_missed_observation_tbl['is_coverable_by_current_filters']
    ].copy()


def select_targets_for_fixed_filterset(
    missed_observation_tbl,
    selected_filterset,
    min_missed_filters=MIN_missed_FILTERS,
):
    selected_filters = {
        filtname
        for filtnames in selected_filterset.values()
        for filtname in filtnames
    }

    use_rows = []
    uncovered_filters_by_row = []
    for row in missed_observation_tbl:
        missed_filters = parse_missed_filters(row['missing_filters_str'])
        uncovered_filters = [
            filtname for filtname in missed_filters
            if filtname not in selected_filters
        ]
        use_rows.append(
            (int(row['n_mb_missing']) > min_missed_filters)
            and (len(uncovered_filters) == 0)
        )
        uncovered_filters_by_row.append(','.join(uncovered_filters))

    checked_tbl = missed_observation_tbl.copy()
    checked_tbl['is_covered_by_selected_filterset'] = use_rows
    selected_filterset_json = json.dumps(selected_filterset, sort_keys=True)
    checked_tbl['selected_filterset_by_tel'] = [
        selected_filterset_json for _ in range(len(checked_tbl))
    ]
    checked_tbl['selected_filterset_uncovered_filters_str'] = uncovered_filters_by_row
    return checked_tbl[checked_tbl['is_covered_by_selected_filterset']].copy(), checked_tbl


def save_selected_filterset(selected_filterset, savepath=SELECTED_FILTERSET_PATH):
    savepath = Path(savepath)
    savepath.parent.mkdir(parents=True, exist_ok=True)
    with open(savepath, 'w') as f:
        json.dump(selected_filterset, f, indent=4)
    return savepath


def main(
    savepath=COVERABLE_OBSERVATION_PATH,
    selected_filterset_savepath=SELECTED_FILTERSET_OBSERVATION_PATH,
    selected_filterset_ascii_savepath=SELECTED_FILTERSET_OBSERVATION_ASCII_PATH,
    selected_filterset_json_savepath=SELECTED_FILTERSET_PATH,
):
    from astropy.table import Table
    from tcspy.devices import MultiTelescopes

    mtel = MultiTelescopes()
    available_filtersets = get_available_filtersets(mtel)
    missed_observation_tbl = Table.read(missed_OBSERVATION_PATH)
    checked_missed_observation_tbl = check_missed_filter_coverage(
        missed_observation_tbl=missed_observation_tbl,
        filtersets=available_filtersets,
    )
    fully_coverable_missed_observation_tbl = select_fully_coverable_targets(
        checked_missed_observation_tbl
    )
    selected_filterset_observation_tbl, checked_selected_filterset_tbl = (
        select_targets_for_fixed_filterset(
            missed_observation_tbl=missed_observation_tbl,
            selected_filterset=SELECTED_FILTERSET,
            min_missed_filters=MIN_missed_FILTERS,
        )
    )

    num_coverable = sum(checked_missed_observation_tbl['is_coverable_by_current_filters'])
    num_selected_filterset = len(selected_filterset_observation_tbl)
    num_cut_targets = sum(missed_observation_tbl['n_mb_missing'] > MIN_missed_FILTERS)
    print(
        f'{num_coverable}/{len(checked_missed_observation_tbl)} rows can be covered '
        f'with up to {MAX_FILTERS_PER_TELESCOPE} filters per telescope.'
    )
    print(
        f'{num_selected_filterset}/{num_cut_targets} rows with '
        f'n_mb_missing > {MIN_missed_FILTERS} are covered by the selected filterset.'
    )

    if savepath is not None:
        fully_coverable_missed_observation_tbl.write(
            savepath,
            format='csv',
            overwrite=True,
        )
        print(f'Fully coverable targets are saved to {savepath}')

    if selected_filterset_savepath is not None:
        selected_filterset_observation_tbl.write(
            selected_filterset_savepath,
            format='csv',
            overwrite=True,
        )
        print(
            'Targets covered by the selected filterset are saved to '
            f'{selected_filterset_savepath}'
        )

    if selected_filterset_ascii_savepath is not None:
        selected_filterset_observation_tbl.write(
            selected_filterset_ascii_savepath,
            format='ascii.fixed_width',
            overwrite=True,
        )
        print(
            'Targets covered by the selected filterset are saved to '
            f'{selected_filterset_ascii_savepath}'
        )

    if selected_filterset_json_savepath is not None:
        saved_filterset_path = save_selected_filterset(
            selected_filterset=SELECTED_FILTERSET,
            savepath=selected_filterset_json_savepath,
        )
        print(f'Selected filterset is saved to {saved_filterset_path}')

    return (
        checked_missed_observation_tbl,
        fully_coverable_missed_observation_tbl,
        checked_selected_filterset_tbl,
        selected_filterset_observation_tbl,
    )


# %%
if __name__ == '__main__':
    (
        checked_missed_observation_tbl,
        fully_coverable_missed_observation_tbl,
        checked_selected_filterset_tbl,
        selected_filterset_observation_tbl,
    ) = main()
    # %%
    checked_selected_filterset_tbl[
        checked_selected_filterset_tbl['selected_filterset_uncovered_filters_str'] != ''
    ][
        [
            'Tile Name',
            'n_mb_missing',
            'missed_filters_str',
            'selected_filterset_uncovered_filters_str',
        ]
    ]

# %%

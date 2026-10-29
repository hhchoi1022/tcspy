#!/usr/bin/env python3
"""Refresh astropy's cached IERS-A table (finals2000A.all) and report its age.

TCSpy sets ``astropy.utils.iers.conf.auto_max_age = None`` (see configuration/mainconfig.py),
so astropy never refreshes the table on its own. Run this periodically instead, e.g. weekly:

    0 12 * * 1  ~/anaconda3/envs/tcs/bin/python ~/code/tcspy/tcspy/utils/update_iers.py >> ~/.cache/update_iers.log 2>&1

Exit code: 0 = table refreshed or still fresh, 1 = download failed and table older than WARN_DAYS.
"""
import sys
from astropy.time import Time
from astropy.utils import iers
from astropy.utils.data import download_file

WARN_DAYS = 90          # complain when the first predictive value is older than this
SOURCES = [             # tried in order; add mirrors here if IERS/USNO stay unreachable
    iers.conf.iers_auto_url,
    iers.conf.iers_auto_url_mirror,
]


def table_age_days(path: str) -> float:
    table = iers.IERS_A.open(path)
    return Time.now().mjd - table.meta['predictive_mjd']


def main() -> int:
    now = Time.now().isot
    for url in SOURCES:
        try:
            path = download_file(url, cache='update', timeout=60)
            print(f'{now} refreshed IERS-A from {url}; predictions start {table_age_days(path):.1f} days ago')
            return 0
        except Exception as e:
            print(f'{now} download failed: {url}: {str(e)[:160]}')
    try:
        path = download_file(SOURCES[0], cache=True)   # cached copy, no network
        age = table_age_days(path)
        print(f'{now} using cached IERS-A; predictions start {age:.1f} days ago')
        return 1 if age > WARN_DAYS else 0
    except Exception as e:
        print(f'{now} no cached IERS-A table: {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())

#%%
# TCSpy modules
from tcspy.configuration import mainConfig
from tcspy.devices.observer import mainObserver
from tcspy.utils.target import mainTarget

from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.table import Table

from astropy.io import ascii
import astropy.units as u

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import datetime
import uuid
import os

from astroplan import FixedTarget, is_event_observable, is_observable, is_always_observable
from astroplan import AltitudeConstraint, AirmassConstraint, MoonSeparationConstraint, AtNightConstraint
from astroplan import observability_table
#%%


class ObsScheduler(mainConfig):
    """
    An observation scheduler class that generates observing schedules based on a target database, time constraints, and the telescope name.
    - History
    (23.04.22) Written by Hyeonho Choi 
    (23.04.23) Change in write_ACPscript_RASA36, write_ACPscript_KCT : change the order to apply #NOSOLVING for all targets
    (23.04.25) ""Version 2.0"", Scheduled table data format changed from Astropy.Table to Pandas.Dataframe
    (23.04.26) Added write_txt function
    (23.04.26) Change the output format of write_txt function
    (23.04.26) Change the structure of the configuration directory depending on the project (ToO, IMSNG)
    (23.04.27) No error anymore when no observable target exists
    (23.04.27 11:10) #Minor change // make_ACPscript_LSGT, fix for the case no target exist in split_table
    (23.05.02) ""Version 3.0"", Running time decreased.
    (23.05.03) Fix for config setting (name_project added)
    (23.06.02) (critical) Fix for the coordinate transformation to string (00:30:30 -> -00:30:30)
    (23.07.10) NINA script converter added by Hongjae Moon
    (23.11.01) Major change in the structure 
        
    ==========
    Parameters
    ==========
    1. target_db : Astropy.table.Table, pandas.Dataframe, Dict
        data containing target information.
        - Must indluded keys
        --------
        obj : object name
        ra : target right ascension, '10:00:00', "10 00 00", "10h 00m 00s", '150.0000'
        dec : target declination, '-30:00:00', "-30 00 00", "-30d 00m 00s", '-30.0000'
        Other keys (filters, exptime, ...) will be set default(from Scheduler_telescope.config) if not provided
        --------
        
    2. date : datetime.datetime, astropy.time.Time, str (default=Time.now())
        The observation date (in UT).
        - Current supported string format
        --------
        str : 20230421, 2023/04/21, 2023.04.21, 230421, 23/04/21, 23.04.21
        astropy.time.Time
        datetime.datetime
        --------
        
    3. project : str (default='ToO')
        The name of the project. For GECKO, just use ToO

    4. name_telescope : str (default='KCT')
        The name of the telescope for which the observation plan is being made.
        - Current supported telescopes
        --------
        (ToO project) name_telescope : 'KCT', 'RASA36', 'CBNUO', 'LSGT', 'SAO', 'LOAO' 'KMTNet_CTIO', 'KMTNet_SAAO', 'KMTNet_SSO'
        (IMSNG project) name_telescope : 'KCT', 'RASA36', 'LSGT', 'CBNUO'
        --------

    5. entire_night : bool (default=False)
        Whether to generate a plan for the entire night or only part of it.
    
    =======
    Methods
    =======
    1. scheduler(**kwargs) -> schedule : object
        Schedule the observing plan with the observable target
        before running scheduler(), self.schedule returns None
        
    2. scorer(obs_tbl : Astropy.table.Table, utctime : datetime or Astropy.time.Time, **kwargs) -> score : np.array
        Return score array for the given targetlist(obs_tbl)
        
    3. show(scheduled_table : astropy.table.Table, **kwargs) -> None
        Visualize the observing plan with the scheduled table 
    
    ==========
    Properties
    ==========
    1. constraint 
        - maxalt, minalt, moon_separation
    2. self.observer : mainObserver class
    3. self.obsnight
        - sunset_astro, sunrise_astro : -18deg sunrise/set time
        - sunset_prepare, sunrise_prepare : -5deg sunrse/set time
        - obs_start, obs_end : observation start/ end time. 
        - midnight : observatio midnight
    4. self.obsinfo
        - is_night : night status of the observing site 
        - moon_phase : moon phase at the site and date
        - observer_info : observing site information
        - sun_radec : RADec of the Sun
        - moon_radec : RADec of the Moon
    5. self.target
        - all : all targetlist input
        - observable : observable targetlist
    6. self.schedule
        Only when scheduler() is already run
        - all: all targetlist with the updated "scheduled" status
        - observable: observable targetlist with the updated "scheduled" status
        - scheduled: scheduled targetlist 
    
    """
    def __init__(self,
                 target_tbl : Table,
                 observer : mainObserver,
                 date = Time.now(),
                 unitnum : int = 1
                 ):
        super().__init__(unitnum = unitnum)
        
        self.target_tbl = target_tbl
        self.observer = observer
        self.constraint = self._get_constraints(**self.config)
        
        self._astroplan_observer = observer.info['observer']
        self._date = date
    
    def is_ever_observable(self,
                           utctime : datetime or Time = None) -> bool:
        """
        Determines whether the target is observable during the specified time

        Parameters
        ----------
        1. utctimes : datetime or Time, optional
            The time at which to check observability. Defaults to the current time.
            
        Returns
        -------
        bool
            True if the target is observable, False otherwise.
        """
        if utctime is None:
            utctime = Time.now()
        if not isinstance(utctime, Time):
            utctime = Time(utctime)
        tonight = self._observer.tonight(utctime)
        starttime = tonight[0]
        endtime = tonight[1]
        time_range = [starttime, endtime]
        return is_observable(constraints = self._constraints, observer = self._astroplan_observer, targets = self.target_astroplan, time_range = time_range)
    

    def is_always_observable(self,
                             utctimes : datetime or Time or np.array = None) -> bool:
        """
        Determines whether the target is always observable during the specified time

        Parameters
        ----------
        1. utctimes : datetime or Time, optional
            The time at which to check observability. Defaults to the current time.
            
        Returns
        -------
        bool
            True if the target is observable, False otherwise.
        """
        if utctimes is None:
            utctimes = Time.now()
        if not isinstance(utctimes, Time):
            utctimes = Time(utctimes)
        return is_always_observable(constraints = self._constraints, observer = self._astroplan_observer, targets = self.target_astroplan, times = utctimes)
    
    def _match_coord_format(self, ra, dec):
        """
        Create a SkyCoord object from input coordinates ra and dec.

        Parameters:
        - ra (float, int, str): Right ascension in various formats.
        - dec (float, int, str): Declination in various formats.

        Returns:
        - skycoord (SkyCoord): SkyCoord object.

        Raises:
        - ValueError: If input format is not supported.
        """
        if isinstance(ra, (float, int, str)):
            ra = str(ra)
            dec = str(dec)
            if (':' in ra) and (':' in dec):
                skycoord = SkyCoord(ra=ra, dec=dec, unit=(u.hourangle, u.deg), frame='icrs')
            elif ('h' in ra) and ('d' in dec):
                skycoord = SkyCoord(ra=ra, dec=dec, unit=(u.hourangle, u.deg), frame='icrs')
            elif (' ' in ra) and (' ' in dec):
                skycoord = SkyCoord(ra=ra, dec=dec, unit=(u.hourangle, u.deg), frame='icrs')
            else:
                skycoord = SkyCoord(ra=ra, dec=dec, unit=(u.deg, u.deg), frame='icrs')
        else:
            try:
                ra0 = str(ra[0])
                dec0 = str(dec[0])
                if (':' in ra0) and (':' in dec0):
                    skycoord = SkyCoord(ra=ra, dec=dec, unit=(u.hourangle, u.deg), frame='icrs')
                elif ('h' in ra0) and ('d' in dec0):
                    skycoord = SkyCoord(ra=ra, dec=dec, unit=(u.hourangle, u.deg), frame='icrs')
                elif (' ' in ra0) and (' ' in dec0):
                    skycoord = SkyCoord(ra=ra, dec=dec, unit=(u.hourangle, u.deg), frame='icrs')
                else:
                    skycoord = SkyCoord(ra=ra, dec=dec, unit=(u.deg, u.deg), frame='icrs')
            except Exception as e:
                raise ValueError(f'Input format is not supported: {str(e)}')
        return skycoord
    
    def _get_constraints(self,
                         TARGET_MINALT : float = None,
                         TARGET_MAXALT : float = None,
                         TARGET_MAX_SUNALT : float = None,
                         TARGET_MOONSEP : float = None,
                         TARGET_MAXAIRMASS : float = None,
                         **kwargs) -> list:
        constraint_all = []
        if (TARGET_MINALT != None) & (TARGET_MAXALT != None):
            constraint_altitude = AltitudeConstraint(min = TARGET_MINALT * u.deg, max = TARGET_MAXALT * u.deg, boolean_constraint = True)
            constraint_all.append(constraint_altitude)
        if (TARGET_MAX_SUNALT != None):
            constraint_atnight = AtNightConstraint(max_solar_altitude = TARGET_MAX_SUNALT * u.deg)
            constraint_all.append(constraint_atnight)
        if TARGET_MOONSEP != None:
            constraint_gallatitude = MoonSeparationConstraint(min = TARGET_MOONSEP * u.deg, max = None)
            constraint_all.append(constraint_gallatitude)
        if TARGET_MAXAIRMASS != None:
            constraint_gallatitude = AirmassConstraint(min = 1, max = TARGET_MAXAIRMASS)
            constraint_all.append(constraint_gallatitude)
        return constraint_all
# %%

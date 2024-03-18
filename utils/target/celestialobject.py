#%%
# Other modules
from astroplan import FixedTarget, is_event_observable, is_observable, is_always_observable
from astroplan import AltitudeConstraint
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
import numpy as np
import datetime
from typing import List
# TCSpy modules
from tcspy.devices.observer import mainObserver
from tcspy.configuration import mainConfig
from tcspy.utils.target.db_target import SQL_Connector

#%%
class CelestialObject(mainConfig):
    """
    Parameters
    ----------
    1. observer : mainObserver
        An instance of mainObserver representing the observer.
    2. target_ra : float, optional
        The right ascension of the target, in hours.
    3. target_dec : float, optional
        The declination of the target, in degrees.
    4. target_alt : float, optional
        The altitude of the target, in degrees.
    5. target_az : float, optional
        The azimuth of the target, in degrees.
    6. target_name : str, optional
        The name of the target.

    Methods
    -------
    1. get_status() -> dict
        Returns a dictionary with information about the current status of the target.
    2. is_event_observable(utctimes: datetime or Time = None) -> bool
        Determines whether the target is observable at the specified time or at the current time.
    3. altaz(utctimes: datetime or Time = None) -> SkyCoord
        Calculate the alt-az coordinates of the target for a given time(s) in UTC.
    4. risetime(utctime: datetime or Time = None, mode: str = 'next', horizon: float = 30) -> Time
        Calculate the next rise time of the target as seen by the observer.
    5. settime(utctime: datetime or Time = None, mode: str = 'nearest', horizon: float = 30) -> Time
        Calculate the time when the target sets below the horizon.
    6. meridiantime(utctime: datetime or Time = None, mode: str = 'nearest') -> Time
        Calculate the time at which the target passes through the observer's meridian.
    7. hourangle(utctimes: datetime or Time = None) -> Angle
        Calculate the hour angle of the target(s) at the specified time(s).
    8. staralt(utctime : datetime or Time or np.array = None)
        Creates a plot of the altitude and azimuth of a celestial object.
    """
    
    def __init__(self,
                 observer : mainObserver,
                 targets_ra : np.array,
                 targets_dec : np.array,
                 targets_name : np.array = None,
                 **kwargs):
        
        super().__init__(unitnum = observer.unitnum)
        self._observer = observer
        self._astroplan_observer = observer.status['observer']
        self._constraints = self._get_constraints(**self.config)
        self.ra = np.array(targets_ra)
        self.dec = np.array(targets_dec)     
        self.coordinate = self._get_coordinate_radec(ra = targets_ra, dec = targets_dec)
        self.target_astroplan = self._get_target(self.coordinate, targets_name)
        self.name = targets_name
        
    def __repr__(self):
        return f'Astroobject[n_objects = {len(self.coordinate)}]'
    
    def rts_date(self,
                 year : int = None,
                 time_grid_resolution : float = 3 # timegrid for checking the observability 
                 ):
        
        # If start_date & end_date are not specified, defaults to current year
        if year == None:
            year = Time.now().datetime.year
        start_date = Time(datetime.datetime(year = year, month = 1, day = 1))
        end_date = Time(datetime.datetime(year = year+1 , month = 1, day = 1))

        expanded_arrays_observability = []
        expanded_arrays_altitude_midnight = []
        expanded_arrays_date = []
        current_date = start_date
        while current_date <= end_date:
            print(f"Calculating observability of the {len(self.coordinate)} targets on {current_date.strftime('%Y-%m-%d')}")
            midnight = Time((self._observer.tonight(current_date)[0].jd + self._observer.tonight(current_date)[1].jd )/2, format = 'jd')
            alt_at_midnight = self.altaz(midnight).alt.value
            expanded_arrays_altitude_midnight.append(alt_at_midnight)
            observablity = self.is_ever_observable(current_date, time_grid_resolution= time_grid_resolution * u.hour)
            expanded_arrays_observability.append(observablity)
            expanded_arrays_date.append(current_date.datetime)
            current_date += 1 * u.day

        observablity_array = np.array(expanded_arrays_observability).T
        altitude_array = np.array(expanded_arrays_altitude_midnight).T
        date_array = np.array(expanded_arrays_date)
        
        all_observability = []
        # Find the indices where the value changes
        for target_observability, target_altitude in zip(observablity_array, altitude_array):
            if all(target_observability):
                risedate = 'Always'
                setdate = 'Always'
                bestdate = date_array[np.argmax(target_altitude)]
            elif all(~target_observability):
                risedate = 'Never'
                setdate = 'Never'
                bestdate = 'Never'
            else:
                # Find index where observability False to True
                risedate_index = np.where(np.diff(target_observability.astype(int)) == 1)[0] + 1
                risedate = date_array[risedate_index[0]]
                # Find index where observability True to False
                setdate_index = np.where(np.diff(target_observability.astype(int)) == -1)[0] + 1
                setdate = date_array[setdate_index[0]]
                bestdate = date_array[np.argmax(target_altitude)]
            all_observability.append((risedate, bestdate, setdate))
        
        return np.array(all_observability)
        
    def is_ever_observable(self,
                           utctime : datetime or Time = None,
                           time_grid_resolution = 1 * u.hour) -> List[bool]:
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
        return is_observable(constraints = self._constraints, observer = self._astroplan_observer, targets = self.target_astroplan, time_range = time_range, time_grid_resolution = time_grid_resolution)
    

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
    
    def is_event_observable(self,
                            utctimes : datetime or Time or np.array = None) -> bool:
        """
        Determines whether the target is observable at the specified time or at the current time.

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
        return is_event_observable(constraints = self._constraints, observer = self._astroplan_observer, target = self.target_astroplan, times = utctimes)
    
    def altaz(self,
              utctimes : datetime or Time or np.array = None) -> SkyCoord:
        """
        Calculate the alt-az coordinates of the target for a given time(s) in UTC.

        Parameters
        ==========
        1. utctimes : datetime or Time, optional
            The time(s) to calculate the alt-az coordinates for, in UTC. If not provided, the current time will be used. 

        Returns
        =======
        1. SkyCoord
            The alt-az coordinates of the target at the specified time(s).
        """
        if utctimes is None:
            utctimes = Time.now()
        if not isinstance(utctimes, Time):
            utctimes = Time(utctimes)
        return self._astroplan_observer.altaz(utctimes, target = self.target_astroplan)
    
    def risetime(self,
                 utctime : datetime or Time = None ,
                 mode : str = 'nearest',
                 horizon : float = 30,
                 n_grid_points : int = 50) -> Time:
        """
        Calculate the next rise time of the target as seen by the observer.

        Parameters
        ==========
        1. utctime : datetime or Time, optional
            The time to start searching for the next rise time. If not provided, the current time will be used.
        2. mode : str, optional
            The method used to determine the rise time. Possible values are 'next' (the next rise time), 'previous' (the previous rise time), or 'nearest' (the nearest rise time). Default is 'next'.
        3. horizon : float, optional
            The altitude of the horizon, in degrees. Default is 30.

        Returns
        =======
        1. Time
            The rise time of the target as seen by the observer.

        """
        if utctime == None:
            utctime = Time.now()
        if not isinstance(utctime, Time):
            utctime = Time(utctime)
        return self._astroplan_observer.target_rise_time(utctime, target = self.target_astroplan, which = mode, horizon = horizon*u.deg, n_grid_points = n_grid_points)
    
    def settime(self,
                utctime : datetime or Time or np.array = None,
                mode : str = 'nearest',
                horizon : float = 30,
                n_grid_points : int = 50) -> Time:
        """
        Calculate the time when the target sets below the horizon.

        Parameters
        ==========
        1. utctime : datetime or Time, optional
            The time to use as the reference time for the calculation, by default the current time.
        2. mode : str, optional
            Set to 'nearest', 'next' or 'previous', by default 'nearest'.
        3. horizon : float, optional
            The altitude of the horizon in degrees. Default is 30.

        Returns
        =======
        1. settime : Time
            The time when the target sets below the horizon.
        """
        if utctime is None:
            utctime = Time.now()
        if not isinstance(utctime, Time):
            utctime = Time(utctime)
        return self._astroplan_observer.target_set_time(utctime, self.target_astroplan, which = mode, horizon = horizon*u.deg , n_grid_points = n_grid_points)
    
    def meridiantime(self,
                     utctime : datetime or Time or np.array = None,
                     mode : str = 'nearest',
                     n_grid_points : int = 50) -> Time:
        """
        Calculate the time at which the target passes through the observer's meridian.

        Parameters
        ==========
        1. utctime : datetime or Time, optional
            The time at which to calculate the meridian transit time. If not provided, the current time will be used.
        2. mode : str, optional
            Set to 'nearest', 'next' or 'previous', by default 'nearest'.
            
        Return
        ======
        1. meridiantime : Time
            The time at which the target passes through the observer's meridian.
        """
        
        if utctime is None:
            utctime = Time.now()
        if not isinstance(utctime, Time):
            utctime = Time(utctime)
        return self._astroplan_observer.target_meridian_transit_time(utctime, self.target_astroplan, which = mode, n_grid_points = n_grid_points)
    
    def hourangle(self,
                  utctimes : datetime or Time or np.array = None):
        """
        Calculate the hour angle of the target for a given time(s) in UTC.

        Parameters
        ==========
        1. utctimes : datetime or Time, optional
            The time(s) to calculate the hour angle of the target for, in UTC. If not provided, the current time will be used. 

        Returns
        =======
        1. hourangle : astropy.coordinates.Angle
            The hour angle of the target(s) at the specified time(s).
        """
        
        if utctimes is None:
            utctimes = Time.now()
        if not isinstance(utctimes, Time):
            utctimes = Time(utctimes)
        if not isinstance(self.target_astroplan, FixedTarget):
            raise ValueError('No target is specified for hourangle')
        return self._astroplan_observer.target_hour_angle(utctimes, self.target_astroplan)
        
    def _get_coordinate_radec(self,
                              ra,
                              dec,
                              frame : str = 'icrs') -> SkyCoord:
        return SkyCoord(ra = ra, dec = dec, frame = frame, unit = (u.deg, u.deg))

    def _get_target(self,
                    coord,
                    target_name : str = '') -> FixedTarget:
        return FixedTarget(coord = coord, name = target_name)
    
    def _get_constraints(self,
                         TARGET_MINALT : float = None,
                         TARGET_MAXALT : float = None,
                         **kwargs) -> list:
        constraint_all = []
        if (TARGET_MINALT != None) & (TARGET_MAXALT != None):
            constraint_altitude = AltitudeConstraint(min = TARGET_MINALT * u.deg, max = TARGET_MAXALT * u.deg, boolean_constraint = True)
            constraint_all.append(constraint_altitude)
        return constraint_all
    
    

# %%

if __name__ == '__main__':
    import time
    S = SQL_Connector()
    target_tbl = S.get_data(tbl_name = 'Daily', select_key = '*')
    observer = mainObserver(unitnum = 21)
    idx = np.random.randint(0, len(target_tbl), size = 100)
    m = AstroObject(observer = observer, targets_ra = target_tbl['RA'][idx], targets_dec = target_tbl['De'][idx], targets_name = target_tbl['objname'][idx])
    start = time.perf_counter()
    rsb = m.risetime()
    print(time.perf_counter() - start)
    
#%%
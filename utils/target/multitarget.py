#%%
# Other modules
from astroplan import FixedTarget, is_event_observable, is_observable, is_always_observable
from astroplan import AltitudeConstraint, AirmassConstraint, MoonSeparationConstraint, GalacticLatitudeConstraint, AtNightConstraint
from astroplan import months_observable
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
import numpy as np
import datetime
import matplotlib.pyplot as plt
from matplotlib import cm
from typing import List
# TCSpy modules
from tcspy.devices.observer import mainObserver
from tcspy.configuration import mainConfig
from tcspy.utils.target.db_target import SQL_Connector
import ephem

#%%
class MultiTarget(mainConfig):
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
                 unitnum : int = 1,
                 **kwargs):
        
        super().__init__(unitnum = unitnum)
        self._observer = observer
        self._astroplan_observer = observer.status['observer']
        self._constraints = self._get_constraints(**self.config)
        self.ra = np.array(targets_ra)
        self.dec = np.array(targets_dec)     
        self.coordinate = self._get_coordinate_radec(ra = targets_ra, dec = targets_dec)
        self.target_astroplan = self._get_target(self.coordinate, targets_name)
        self.name = targets_name
        
    def __repr__(self):
        return f'MultiTarget[n_target = {len(self.coordinate)}]'
    
    def rise_best_set_date(self,
                           date : Time = None,
                           time_grid_resolution = 1 # day
                           ):
        
        # If start_date & end_date are not specified, defaults to current year
        if date == None:
            date = Time.now()
        start_year = date.datetime.year
        start_date = Time(datetime.datetime(year = start_year, month = 1, day = 1))
        end_date = Time(datetime.datetime(year = start_year +1 , month = 12, day = 31))

        expanded_arrays_observability = []
        expanded_arrays_date = []
        current_date = start_date
        while current_date <= end_date:
            observablity = self.is_event_observable(current_date)
            expanded_arrays_observability.append(observablity)
            expanded_arrays_date.append(current_date.datetime)
            current_date += time_grid_resolution * u.day

        observablity_array = np.hstack(expanded_arrays_observability)
        date_array = np.array(expanded_arrays_date)
        
        all_observability = []
        # Find the indices where the value changes
        for target_observability in observablity_array:
            if all(target_observability):
                risedate = 'Always'
                setdate = 'Always'
                bestdate = 'Always'
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
                if risedate > setdate:
                    setdate_after_risedate = date_array[setdate_index[1]]
                else:
                    setdate_after_risedate = setdate
                bestdate_timestamp  = (risedate.timestamp() + setdate_after_risedate.timestamp()) / 2
                bestdate = datetime.datetime.fromtimestamp(bestdate_timestamp)
            all_observability.append((risedate, setdate, bestdate))
        
        return np.array(all_observability)
        
    def is_ever_observable(self,
                           utctime : datetime or Time = None) -> List[bool]:
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
    target_tbl = S.get_data(tbl_name = 'RIS', select_key = '*')
    observer = mainObserver(unitnum = 21)
    idx = np.random.randint(0, len(target_tbl), size = 100)
    m = MultiTarget(observer = observer, targets_ra = target_tbl['RA'][idx], targets_dec = target_tbl['De'][idx], targets_name = target_tbl['objname'][idx])
    start = time.perf_counter()
    print(time.perf_counter() - start)
    
#%%

# %%


observer = ephem.Observer()
observer.lat = '-30.4704'  # Latitude in degrees (for example, London's latitude)
observer.lon = '-70.7804'    # Longitude in degrees (for example, London's longitude)
observer.elevation = 1580    # Elevation in meters (optional)
observer.horizon = 40
#%%

target = ephem.FixedBody()
target._ra = ephem.hours('20:14:32')  # Example RA coordinate in hours
target._dec = ephem.degrees('-30:26:29')  # Example Dec coordinate in degrees

#%%
dt = datetime.utcnow()
rise_time = print(observer.next_rising(target, start = dt))

start_date = Time('2024-01-01').to_datetime()
end_date = Time('2025-12-31').to_datetime()
current_date = start_date
while current_date <= end_date:
    observer.date = current_date
    rise_time = observer.next_rising(target)
    if (rise_time.datetime() - current_date).total_seconds()/86400 > 1:
        print(rise_time)
    if (rise_time.datetime() - current_date).total_seconds()/86400 < -1:
        print(rise_time)
    current_date += timedelta(days = 1)
# %%
start_date = Time('2023-9-01').to_datetime()
end_date = Time('2024-12-31').to_datetime()
from datetime import datetime
start_date = datetime.utcnow()
end_date = start_date + timedelta(days=300)
# Iterate over dates within the search range
rise_date = None
set_date = None
while current_date <= end_date:
    observer.date = current_date.strftime('%Y/%m/%d %H:%M:%S')
    
    try:
        rise_time = observer.next_rising(target)
        if observer.previous_setting(target) < rise_time:
            rise_date = current_date
            break
    except ephem.NeverUpError:
        pass
    
    current_date += timedelta(days=1)

# Reset current_date for finding set date
current_date = rise_date if rise_date else start_date

while current_date <= end_date:
    observer.date = current_date.strftime('%Y/%m/%d %H:%M:%S')
    
    try:
        set_time = observer.next_setting(target)
        if observer.previous_rising(target) < set_time:
            set_date = current_date
            break
    except ephem.NeverUpError:
        pass
    
    current_date += timedelta(days=1)

if rise_date:
    print("Rise date:", rise_date.strftime('%Y-%m-%d'))
else:
    print("Target does not rise within the specified range.")

if set_date:
    print("Set date:", set_date.strftime('%Y-%m-%d'))
else:
    print("Target does not set within the specified range.")

# %%
sitka = ephem.Observer()
sitka.date = '1999/6/27'
sitka.lat = '57:10'
sitka.lon = '-135:15'
# %%
m = ephem.Mars()
# %%
print(sitka.next_transit(m))
# %%

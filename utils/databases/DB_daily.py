

#%%
from tcspy.utils.target import MultiTargets
from tcspy.utils.target import SingleTarget
from tcspy.configuration import mainConfig
from tcspy.utils.databases import SQL_Connector
from tcspy.devices.observer import mainObserver

from astropy.table import Table 
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import SkyCoord
import numpy as np
from astroplan import observability_table
from astroplan import AltitudeConstraint, MoonSeparationConstraint
from tqdm import tqdm

# %%

class DB_Daily(mainConfig):
    """
    class of Daily target table for the observation of each night.

    Parameters
    ----------
    utctime : astropy.time.Time
        The current universal time.
    tbl_name : str
        The name of the database table used for this observing information.

    Attributes
    ----------
    observer : mainObserver
        The station observing the night sky.
    tblname : str
        The name of the table used to track the observing information.
    sql : SQL_Connector
        A connection to the SQL database.
    constraints : constraint
        The observer's constraints.
    utctime : astropy.time.Time
        The current universal time.
    obsinfo : object
        The observer and celestial body information.
    obsnight : object
        The observing information at sunset and sunrise.
    connected
        Whether the connection to the database is alive.

    Methods
    -------
    connect(self)
        Establish a connection to the MySQL database and set the cursor and executor.
    disconnect(self)
        Disconnect from the MySQL database and update the connection status flag to False.
    initialize(self, initialize_all)
        Initialize the target status if it requires updates.
    best_target(self, utctime, duplicate)
        Returns the best target to observe.
    insert(self, target_tbl)
        Insert a new record into the table.
    update_target(self, update_value, update_key, id_value, id_key)
        Update an existing target's attribute.
    data(self)
        Return the entire information stored in the table.
    """
    
    def __init__(self,
                 utctime : Time = Time.now(),
                 tbl_name : str = 'Daily'):

        super().__init__()       
        self.observer = mainObserver()
        self.tblname = tbl_name
        self.sql = SQL_Connector(id_user = self.config['DB_ID'], pwd_user= self.config['DB_PWD'], host_user = self.config['DB_HOSTIP'], db_name = self.config['DB_NAME'])
        self.constraints = self._set_constrints()
        self.utctime = utctime
        self.obsinfo = self._set_obs_info(utctime = utctime)
        self.obsnight = self._set_obsnight(utctime = utctime, horizon_prepare = self.config['TARGET_SUNALT_PREPARE'], horizon_astro = self.config['TARGET_SUNALT_ASTRO'])
    
    @property    
    def connected(self):
        return self.sql.connected
    
    def connect(self):
        """
        Establish a connection to the MySQL database and set the cursor and executor.
        """
        self.sql.connect()
    
    def disconnect(self):
        """
        Disconnects from the MySQL database and update the connection status flag to 
        """
        self.sql.disconnect()
    
    def initialize(self, 
                   initialize_all : bool = False):       
        """
        Initializes the target status if it requires updates.

        Parameters
        ----------
        initialize_all : bool
            Boolean flag to control whether all targets should be initialized or not. Defaults to False.
        """
        self.connect()
        target_tbl_all = self.data
        
        # If there is targets with no "id", set ID for each target
        rows_to_update_id = [any(row[name] in (None, '') for name in ['id']) for row in target_tbl_all]
        if np.sum(rows_to_update_id) > 0:
            self.sql.set_data_id(tbl_name = self.tblname, update_all = False)
            target_tbl_all = self.data
        
        target_tbl_to_update = target_tbl_all
        column_names_to_update = ['id', 'binning', 'risetime', 'transittime', 'settime', 'besttime', 'maxalt', 'moonsep']
        
        # If initialize_all == False, filter the target table that requires update 
        if not initialize_all:
            rows_to_update = [any(row[name] is None or row[name] == '' for name in column_names_to_update) for row in target_tbl_all]
            target_tbl_to_update =  target_tbl_all[rows_to_update]
        
        if len(target_tbl_to_update) == 0:
            return 
        
        multitargets = MultiTargets(observer = self.observer,
                                   targets_ra = target_tbl_to_update['RA'],
                                   targets_dec = target_tbl_to_update['De'],
                                   targets_name = target_tbl_to_update['objname'])
        print(f'Calculating celestial information of {len(multitargets.coordinate)} targets...')
        
        # Target information 
        risetime_tmp = self._get_risetime(multitargets = multitargets, utctime = self.obsnight.sunrise_civil, mode = 'previous', horizon = self.config['TARGET_MINALT'], n_grid_points= 100)
        settime_tmp = self._get_settime(multitargets = multitargets, utctime = self.obsnight.sunset_civil, mode = 'next', horizon = self.config['TARGET_MINALT'], n_grid_points= 100)
        # If targets are always up
        risetime = Time([self.obsnight.sunset_astro if np.isnan(rt.value.data) else rt for rt in risetime_tmp])
        settime_tmp2 = Time([self.obsnight.sunset_astro + 1 * u.day if np.isnan(st.value.data) else st for st in settime_tmp])
        # If targets are never up
        settime = Time([st - 1*u.day if (st - rt).value > 1 else st for rt, st in zip(risetime, settime_tmp2)])
        transittime, maxalt, besttime = self._get_transit_besttime(multitargets = multitargets)
        moonsep = self._get_moonsep(multitargets = multitargets)
        targetinfo_listdict = [{'risetime' : rt, 'transittime' : tt, 'settime' : st, 'besttime' : bt, 'maxalt' : mt, 'moonsep': ms} for rt, tt, st, bt, mt, ms in zip(risetime.isot, transittime.isot, settime.isot, besttime.isot, maxalt, moonsep)]
        #i = -2
        #SingleTarget(ra = target_tbl_to_update['RA'][i], dec = target_tbl_to_update['De'][i], observer = self.observer).staralt()

        # Exposure information
        exposureinfo_listdict = []
        for target in target_tbl_to_update:
            try:
                S = SingleTarget(observer = self.observer, 
                                exptime = target['exptime'], 
                                count = target['count'], 
                                filter_ = target['filter_'], 
                                binning = target['binning'], 
                                specmode = target['specmode'],
                                obsmode = target['obsmode'],
                                ntelescope = target['ntelescope'])
                exposure_info = S.exposure_info
                del exposure_info['specmode_filter']
                exposureinfo_listdict.append(exposure_info)
            except:
                exposureinfo_listdict.append(dict(status = 'error'))

        values_update = [{**targetinfo_dict, **exposureinfo_dict} for targetinfo_dict, exposureinfo_dict in zip(targetinfo_listdict, exposureinfo_listdict)]
                
        for i, value in enumerate(tqdm(values_update)):
            target_to_update = target_tbl_to_update[i]  
            self.sql.update_row(tbl_name = self.tblname, update_value = list(value.values()), update_key = list(value.keys()), id_value= target_to_update['id'], id_key = 'id')
        print(f'{len(target_tbl_to_update)} targets are updated')
    
    def best_target(self,
                    utctime : Time = Time.now()):
        """
        Returns the best target to observe.

        Parameters
        ----------
        utctime : astropy.time.Time
            The current universal time. Defaults to the current time.
        duplicate : bool
            Whether to allow duplicate targets. Defaults to False.
        """
        all_targets = self.data
        column_names_for_scoring = ['exptime_tot', 'id', 'risetime', 'transittime', 'settime', 'besttime', 'maxalt', 'moonsep']
        
        # If one of the targets do not have the required information, calculate
        rows_to_update = [any(row[name] is None or row[name] == '' for name in column_names_for_scoring) for row in all_targets]
        target_tbl_to_update =  all_targets[rows_to_update]
        if len(target_tbl_to_update) > 0:
            self.initialize(initialize_all= False)
        
        target_all = self.data
        idx_ToO = all_targets['objtype'] == 'ToO'
        target_ToO = target_all[idx_ToO]
        target_ordinary = target_all[~idx_ToO]
        
        exist_ToO = (len(target_ToO) > 0)
        if exist_ToO:
            target_best, target_score = self._scorer(utctime = utctime, target_tbl = target_ToO)        
            if target_score:
                return target_best, target_score
        
        exist_ordinary = (len(target_ordinary) > 0)
        if exist_ordinary:
            target_best, target_score = self._scorer(utctime = utctime, target_tbl = target_ordinary)        
            if target_score:
                return target_best, target_score
        return None, None
    
    def insert(self,
               target_tbl : Table):
        """
        Inserts a new record into the table.

        Parameters
        ----------
        target_tbl : Table
            An astropy table containing the target data to be inserted.
        """
        self.sql.insert_rows(tbl_name = self.tblname, data = target_tbl)
        
    def update_target(self,
                      update_value,
                      update_key,
                      id_value,
                      id_key = 'id'):
        """
        Updates an existing target's attribute.

        Parameters
        ----------
        update_value: various
            The new value to be updated.
        update_key: str
            The attribute key to be updated.
        id_value: int, str, etc
            The id value of the target to be updated.
        id_key: str
            The attribute key used to identify the target. 
        """
        self.sql.update_row(tbl_name = self.tblname,
                            update_value = update_value,
                            update_key = update_key,
                            id_value = id_value,
                            id_key = id_key)
        
    @property
    def data(self):
        """
        Returns the entire data stored in the table.

        Parameters
        ----------
        None

        Returns
        -------
        Table
            An astropy table containing all the data in the observing table.
        """
        if not self.sql.connected:
            self.connect()
        return self.sql.get_data(tbl_name = self.tblname, select_key= '*')
    
    def _scorer(self,
                utctime : Time,
                target_tbl : Table
                ):
        
        def calc_constraints(target_tbl_for_scoring):
            multitargets = MultiTargets(observer = self.observer,
                                    targets_ra = target_tbl_for_scoring['RA'],
                                    targets_dec = target_tbl_for_scoring['De'],
                                    targets_name = target_tbl_for_scoring['objname'])
            
            multitarget_altaz = multitargets.altaz(utctimes = utctime)
            multitarget_alt = multitarget_altaz.alt.value
            
            score = np.ones(len(target_tbl_for_scoring))
            # Applying constraints
            constraint_moonsep = target_tbl_for_scoring['moonsep'].astype(float) > self.constraints.moon_separation
            score *= constraint_moonsep
            
            constraint_altitude_min = multitarget_alt > self.constraints.minalt
            score *= constraint_altitude_min
            
            constraint_altitude_max = multitarget_alt < self.constraints.maxalt
            score *= constraint_altitude_max
            
            constraint_set = (utctime + target_tbl_for_scoring['exptime_tot'].astype(float) * u.s < Time(target_tbl_for_scoring['settime'])) & (utctime + target_tbl_for_scoring['exptime_tot'].astype(float) * u.s < self.obsnight.sunrise_astro)
            score *= constraint_set
            
            constraint_night = self.observer.is_night(utctimes = utctime)
            #score *= constraint_night
            return score, multitarget_alt
        
        # Start
        target_tbl_for_scoring = target_tbl
        # Exclude scheduled targets
        unscheduled_idx = (target_tbl['status'] == 'unscheduled')
        target_tbl_for_scoring = target_tbl[unscheduled_idx]
        
        # Exit when no observable target
        if len(target_tbl_for_scoring) == 0:
            return None, None
        
        # When target observation time is specified
        obstime_fixed_targets = target_tbl_for_scoring[target_tbl_for_scoring['obstime'] != None]
        urgent_targets = Table()
        if len(obstime_fixed_targets) > 0:
            obstime = Time([Time(time) for time in obstime_fixed_targets['obstime']])
            time_left_sec = (obstime - utctime).sec
            urgent_targets = obstime_fixed_targets[(time_left_sec < 0) & (obstime < self.obsnight.sunrise_astro) & (obstime > self.obsnight.sunset_astro)]
            if len(urgent_targets) > 0:
                score, alt = calc_constraints(urgent_targets)
                urgent_targets_scored = urgent_targets[score.astype(bool)]
                # If urgent target observable exists, return the target and score 1
                if len(urgent_targets_scored) > 0:
                    urgent_obstime = Time([Time(time) for time in urgent_targets_scored['obstime']])
                    urgent_targets_scored['obstime'] = urgent_obstime
                    urgent_targets_scored.sort('obstime')
                    return urgent_targets_scored[0], 1
        
        # Scoring
        score, multitarget_alt = calc_constraints(target_tbl_for_scoring)
                
        # Exit when no observable target
        if np.sum(score) == 0:
            return None, None
        
        multitarget_priority = target_tbl_for_scoring['priority'].astype(float)
        weight_sum = self.config['TARGET_WEIGHT_ALT'] + self.config['TARGET_WEIGHT_PRIORITY']
        weight_alt = self.config['TARGET_WEIGHT_ALT'] / weight_sum
        weight_priority = self.config['TARGET_WEIGHT_PRIORITY'] / weight_sum
        
        multitarget_alt = np.array([0 if target_alt <= 0 else target_alt for target_alt in multitarget_alt])
        score_relative_alt = weight_alt * np.clip(0, 1, (multitarget_alt) / (np.abs(target_tbl_for_scoring['maxalt'])))
        
        highest_priority = np.max(multitarget_priority)
        score_weight = weight_priority* (multitarget_priority / highest_priority)

        score_all = (score_relative_alt  + score_weight) 
        score *= score_all
        idx_best = np.argmax(score)
        score_best = score[idx_best]
        return target_tbl_for_scoring[idx_best], score_best

    def _set_obs_info(self,
                      utctime : Time = Time.now()):
        class info: pass
        info.moon_phase = self.observer.moon_phase(utctime)
        info.moon_radec = self.observer.moon_radec(utctime)
        info.sun_radec = self.observer.sun_radec(utctime)
        info.observer_info = self.observer.get_status()
        info.observer_astroplan = self.observer._observer
        info.is_night = self.observer.is_night(utctime)
        return info
    
    def _set_obsnight(self,
                      utctime : Time = Time.now(),
                      horizon_prepare : float = -5,
                      horizon_astro : float = -18):
        class night: pass
        night.sunrise_civil = self.observer.tonight(time = utctime, horizon = 0)[1]
        night.sunset_civil = self.observer.sun_settime(night.sunrise_civil, mode = 'previous', horizon= 0)        
        night.sunrise_prepare = self.observer.sun_risetime(night.sunrise_civil, mode = 'previous', horizon= horizon_prepare)
        night.sunset_prepare = self.observer.sun_settime(night.sunrise_civil, mode = 'previous', horizon= horizon_prepare)
        night.sunrise_astro = self.observer.sun_risetime(night.sunrise_civil, mode = 'previous', horizon= horizon_astro)
        night.sunset_astro = self.observer.sun_settime(night.sunrise_civil, mode = 'previous', horizon= horizon_astro)
        #night.sunrise_civil = self.observer.sun_risetime(night.sunrise_prepare, mode = 'previous', horizon= 0)
        #night.sunset_civil = self.observer.sun_settime(night.sunrise_prepare, mode = 'previous', horizon= 0)        
        night.midnight = Time((night.sunset_astro.jd + night.sunrise_astro.jd)/2, format = 'jd')
        night.time_inputted = utctime
        night.current = Time.now()
        return night

    def _set_constrints(self):
        class constraint: pass
        constraint_astroplan = []
        if (self.config['TARGET_MINALT'] != None) & (self.config['TARGET_MAXALT'] != None):
            constraint_altitude = AltitudeConstraint(min = self.config['TARGET_MINALT'] * u.deg, max = self.config['TARGET_MAXALT'] * u.deg, boolean_constraint = False)
            constraint_astroplan.append(constraint_altitude)
            constraint.minalt = self.config['TARGET_MINALT']
            constraint.maxalt = self.config['TARGET_MAXALT']
        if self.config['TARGET_MOONSEP'] != None:
            constraint_gallatitude = MoonSeparationConstraint(min = self.config['TARGET_MOONSEP'] * u.deg, max = None)
            constraint_astroplan.append(constraint_gallatitude)
            constraint.moon_separation = self.config['TARGET_MOONSEP']
        constraint.astroplan = constraint_astroplan
        return constraint
    
    def _get_moonsep(self,
                     multitargets : MultiTargets):
        '''
        multitargets = MultiTargets(observer = self.observer, 
                            targets_ra = target_tbl['RA'], 
                            targets_dec = target_tbl['De'],    
                            targets_name = target_tbl['objname'])
        '''
        all_coords = multitargets.coordinate
        moon_coord = SkyCoord(ra =self.obsinfo.moon_radec.ra.value, dec = self.obsinfo.moon_radec.dec.value, unit = 'deg')
        moonsep = np.array(SkyCoord.separation(all_coords, moon_coord).value).round(2)
        return moonsep        
        
    def _get_risetime(self,
                      multitargets : MultiTargets,
                      **kwargs):
        if len(multitargets.coordinate) == 1:
            risetime = [multitargets.risetime(**kwargs)]
        else:
            risetime = multitargets.risetime(**kwargs)
        return Time(risetime)
    
    def _get_settime(self,
                     multitargets : MultiTargets,
                     **kwargs):
        if len(multitargets.coordinate) == 1:
            settime = [multitargets.settime(**kwargs)]
        else:
            settime = multitargets.settime(**kwargs)
        return Time(settime)
        
    def _get_transit_besttime(self,
                              multitargets : MultiTargets):
        
        all_time_hourangle = multitargets.hourangle(self.obsnight.midnight)
        all_hourangle_converted = [hourangle if (hourangle -12 < 0) else hourangle-24 for hourangle in all_time_hourangle.value]
        all_target_altaz_at_sunset = multitargets.altaz(utctimes=self.obsnight.sunset_astro)
        all_target_altaz_at_sunrise = multitargets.altaz(utctimes=self.obsnight.sunrise_astro)
        all_transittime = self.obsnight.midnight - all_hourangle_converted * u.hour
        all_besttime = []
        all_maxalt = []
        for i, target_info in enumerate(zip(all_transittime, multitargets.coordinate)):
            target_time_transit, target_coord = target_info
            if (target_time_transit > self.obsnight.sunset_astro) & (target_time_transit < self.obsnight.sunrise_astro):
                maxaltaz = self.obsinfo.observer_astroplan.altaz(target_time_transit, target = target_coord)
                maxalt = np.round(maxaltaz.alt.value,2)
                all_besttime.append(target_time_transit)
            else:
                sunset_alt = all_target_altaz_at_sunset[i].alt.value
                sunrise_alt = all_target_altaz_at_sunrise[i].alt.value
                maxalt = np.round(np.max([sunset_alt, sunrise_alt]),2)
                if sunset_alt > sunrise_alt:
                    all_besttime.append(self.obsnight.sunset_astro)
                else:
                    all_besttime.append(self.obsnight.sunrise_astro)
            all_maxalt.append(maxalt)
        return all_transittime, all_maxalt, Time(all_besttime)

    def _get_target_observable(self,
                               multitargets : MultiTargets,
                               fraction_observable : float = 0.1):
        observability_tbl = observability_table(constraints = self.constraints, observer = multitargets._astroplan_observer, targets = multitargets.coordinate , time_range = [self.obsnight.sunset_astro, self.obsnight.sunrise_astro], time_grid_resolution = 20 * u.minute)
        obs_tbl['fraction_obs'] = ['%.2f'%fraction for fraction in observability_tbl['fraction of time observable']]
        key = observability_tbl['fraction of time observable'] > fraction_observable
        obs_tbl = obs_tbl[key]

# %%
if __name__ == '__main__':
    D = DB_Daily()
    D.initialize()
# %%



#%%
from tcspy.utils.target import CelestialObject
from tcspy.configuration import mainConfig
from tcspy.utils.target.db_target import SQL_Connector
from tcspy.devices.observer import mainObserver

from astropy.table import Table 
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import SkyCoord
import numpy as np
from astroplan import observability_table
from astroplan import AltitudeConstraint, MoonSeparationConstraint

# %%

class RISTarget(mainConfig):
    
    def __init__(self,
                 utctime : Time = Time.now(),
                 tbl_name : str = 'RIS'):
        super().__init__()       
        self.observer = mainObserver(unitnum= 1)
        self.tblname = tbl_name
        self.sql = SQL_Connector(id_user = self.config['DB_ID'], pwd_user= self.config['DB_PWD'], host_user = self.config['DB_HOSTIP'], db_name = self.config['DB_NAME'])
        self.constraints = self._set_constrints()
        self.utctime = utctime
        self.obsinfo = self._set_obs_info(utctime = utctime)
        self.obsnight = self._set_obsnight(utctime = utctime, horizon_prepare = self.config['TARGET_SUNALT_PREPARE'], horizon_astro = self.config['TARGET_SUNALT_ASTRO'])

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
        night.sunrise_prepare = self.observer.tonight(time = utctime, horizon = horizon_prepare)[1]
        night.sunset_prepare = self.observer.sun_settime(night.sunrise_prepare, mode = 'previous', horizon= horizon_prepare)
        night.sunrise_astro = self.observer.sun_risetime(night.sunrise_prepare, mode = 'previous', horizon= horizon_astro)
        night.sunset_astro = self.observer.sun_settime(night.sunrise_prepare, mode = 'previous', horizon= horizon_astro)
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
        constraint.astroplan = constraint_astroplan
        return constraint  
        
    def connect(self):
        self.sql.connect()
    
    def disconnect(self):
        self.sql.disconnect()
    
    def initialize(self, 
                   initialize_all : bool = False):        
        self.connect()
        target_tbl_all = self.data
        
        # If there is targets with no "id", set ID for each target
        rows_to_update_id = [any(row[name] is None for name in ['id']) for row in target_tbl_all]
        if np.sum(rows_to_update_id) > 0:
            self.sql.set_data_id(tbl_name = self.tblname, update_all = False)
            target_tbl_all = self.data
        
        target_tbl_to_update = target_tbl_all
        column_names_to_update = ['risedate', 'bestdate', 'setdate']
        
        # If initialize_all == False, filter the target table that requires update 
        if not initialize_all:
            rows_to_update = [any(row[name] is None or row[name] == '' for name in column_names_to_update) for row in target_tbl_all]
            target_tbl_to_update =  target_tbl_all[rows_to_update]
        
        if len(target_tbl_to_update) == 0:
            return 
        
        celestialobject = CelestialObject(observer = self.observer,
                                          targets_ra = target_tbl_to_update['RA'],
                                          targets_dec = target_tbl_to_update['De'],
                                          targets_name = target_tbl_to_update['objname'])
        
        # Target information 
        risedate, bestdate, setdate = celestialobject.rts_date(year = self.utctime.datetime.year, time_grid_resolution= 0.3)
        targetinfo_listdict = [{'risetime' : rt, 'transittime' : tt, 'settime' : st, 'besttime' : bt, 'maxalt' : mt, 'moonsep': ms} for rt, tt, st, bt, mt, ms in zip(risetime.isot, transittime.isot, settime.isot, besttime.isot, maxalt, moonsep)]
        
        from tcspy.utils.target import SingleTarget
        
        # Exposure information
        exposureinfo_listdict = []
        for target in target_tbl_to_update:
            try:
                S = SingleTarget(observer = self.observer, 
                                exptime = target['exptime'], 
                                count = target['count'], 
                                filter_ = target['filter'], 
                                binning = target['binning'], 
                                obsmode = target['obsmode'],
                                ntelescope = target['ntelescope'])
                exposureinfo_listdict.append(S.exposure_info)
            except:
                exposureinfo_listdict.append(dict(status = 'error'))

        values_update_dict = [{**targetinfo_dict, **exposureinfo_dict} for targetinfo_dict, exposureinfo_dict in zip(targetinfo_listdict, exposureinfo_listdict)]
                
        for i, value in enumerate(values_update_dict):
            target_to_update = target_tbl_to_update[i]  
            self.sql.update_row(tbl_name = self.tblname, update_value = list(value.values()), update_key = list(value.keys()), id_value= target_to_update['id'], id_key = 'id')
        print(f'{len(target_tbl_to_update)} targets are updated')
    
    def _scorer(self,
                utctime : Time,
                target_tbl : Table,
                duplicate : bool = False):
        
        target_tbl_for_scoring = target_tbl
        if not duplicate:
            unscheduled_idx = (target_tbl['status'] == 'unscheduled')
            target_tbl_for_scoring = target_tbl[unscheduled_idx]
        
        celestialobject = CelestialObject(observer = self.observer,
                                  targets_ra = target_tbl_for_scoring['RA'],
                                  targets_dec = target_tbl_for_scoring['De'],
                                  targets_name = target_tbl_for_scoring['objname'])
        
        celestialobject_altaz = celestialobject.altaz(utctimes = utctime)
        celestialobject_alt = celestialobject_altaz.alt.value
        celestialobject_priority = target_tbl_for_scoring['priority'].astype(float)
        
        score = np.ones(len(target_tbl_for_scoring))
        # Applying constraints
        constraint_moonsep = target_tbl_for_scoring['moonsep'].astype(float) > self.constraints.moon_separation
        score *= constraint_moonsep
        
        constraint_altitude_min = celestialobject_alt > self.constraints.minalt
        score *= constraint_altitude_min
        
        constraint_altitude_max = celestialobject_alt < self.constraints.maxalt
        score *= constraint_altitude_max
        
        constraint_set = (utctime + target_tbl_for_scoring['exptime_tot'].astype(float) * u.s < Time(target_tbl_for_scoring['settime'])) & (utctime + target_tbl_for_scoring['exptime_tot'].astype(float) * u.s < self.obsnight.sunrise_astro)
        score *= constraint_set
        
        constraint_night = self.observer.is_night(utctimes = utctime)
        score *= constraint_night
        
        # Scoring
        weight_sum = self.config['TARGET_WEIGHT_ALT'] + self.config['TARGET_WEIGHT_PRIORITY']
        weight_alt = self.config['TARGET_WEIGHT_ALT'] / weight_sum
        weight_priority = self.config['TARGET_WEIGHT_PRIORITY'] / weight_sum
        
        celestialobject_alt = np.array([0 if target_alt <= 0 else target_alt for target_alt in celestialobject_alt])
        score_relative_alt = weight_alt * np.clip(0, 1, (celestialobject_alt) / (np.abs(target_tbl_for_scoring['maxalt'])))
        
        highest_priority = np.max(celestialobject_priority)
        score_weight = weight_priority* (celestialobject_priority / highest_priority)

        score_all = (score_relative_alt  + score_weight) 
        score *= score_all
        idx_best = np.argmax(score)
        score_best = score[idx_best]
        return target_tbl_for_scoring[idx_best], score_best
    
    def best_target(self,
                    utctime : Time = Time.now(),
                    duplicate : bool = False):
        if not self.sql.connected:
            self.connect()
        all_targets = self.data
        column_names_for_scoring = ['exptime','count','filter','exptime_tot', 'ntelescope', 'binning', 'risetime', 'transittime', 'settime', 'besttime', 'maxalt', 'moonsep']
        
        # If one of the targets do not have the required information, calculate
        rows_to_update = [any(row[name] is None or row[name] == '' for name in column_names_for_scoring) for row in all_targets]
        target_tbl_to_update =  all_targets[rows_to_update]
        if len(target_tbl_to_update) > 0:
            self.initialize(initialize_all= False)
        
        import time
        start = time.perf_counter()
        target_all = self.data
        idx_ToO = all_targets['objtype'] == 'ToO'
        target_ToO = target_all[idx_ToO]
        target_ordinary = target_all[~idx_ToO]
        
        exist_ToO = (len(target_ToO) > 0)
        if exist_ToO:
            target_best, target_score = self._scorer(utctime = utctime, target_tbl = target_ToO, duplicate = duplicate)        
            if target_score > 0:
                return target_best, target_score
        
        target_best, target_score = self._scorer(utctime = utctime, target_tbl = target_ordinary, duplicate = duplicate)        
        if target_score > 0:
            return target_best, target_score
        else:
            return None, target_score
    
    @property
    def data(self):
        if not self.sql.connected:
            self.connect()
        return self.sql.get_data(tbl_name = self.tblname, select_key= '*')

    

# %%
D =  DailyTarget()
# %%
A = D.initialize(initialize_all= False)
# %%
D.best_target(Time.now() - 3 * u.hour)
#%%
D._get_moonsep(target_tbl =  D.get_data()[150:220])
# %%
D._get_maxaltaz(target_tbl =  D.get_data()[150:220])[1]
# %%
Time(D._get_maxaltaz(target_tbl = D.get_data()[150:220])[2]).isot
# %%
D.get_data()
# %%
import matplotlib.pyplot as plt
plt.plot(Time(D._get_maxaltaz(target_tbl = D.get_data()[150:220])[2]).value)
# %%
D.get_data()[200:250]['RA']
# %%
for value in D.get_data()[150:220]:
    print(value['RA'], ' ', value['De'])
# %%

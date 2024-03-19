

#%%
from tcspy.utils.target import CelestialObject
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
import tqdm

# %%

class DB_RIS(mainConfig):
    
    def __init__(self,
                 utcdate : Time = Time.now(),
                 tbl_name : str = 'RIS'):
        super().__init__()       
        self.observer = mainObserver(unitnum= 1)
        self.tblname = tbl_name
        self.sql = SQL_Connector(id_user = self.config['DB_ID'], pwd_user= self.config['DB_PWD'], host_user = self.config['DB_HOSTIP'], db_name = self.config['DB_NAME'])
        self.constraints = self._set_constrints()
        self.utcdate = utcdate
        self.obsinfo = self._set_obs_info(utcdate = utcdate)
        self.obsnight = self._set_obsnight(utcdate = utcdate, horizon_prepare = self.config['TARGET_SUNALT_PREPARE'], horizon_astro = self.config['TARGET_SUNALT_ASTRO'])

    def _set_obs_info(self,
                      utcdate : Time = Time.now()):
        class info: pass
        info.moon_phase = self.observer.moon_phase(utcdate)
        info.moon_radec = self.observer.moon_radec(utcdate)
        info.sun_radec = self.observer.sun_radec(utcdate)
        info.observer_info = self.observer.get_status()
        info.observer_astroplan = self.observer._observer
        info.is_night = self.observer.is_night(utcdate)
        return info
    
    def _set_obsnight(self,
                      utcdate : Time = Time.now(),
                      horizon_prepare : float = -5,
                      horizon_astro : float = -18):
        class night: pass
        night.sunrise_prepare = self.observer.tonight(time = utcdate, horizon = horizon_prepare)[1]
        night.sunset_prepare = self.observer.sun_settime(night.sunrise_prepare, mode = 'previous', horizon= horizon_prepare)
        night.sunrise_astro = self.observer.sun_risetime(night.sunrise_prepare, mode = 'previous', horizon= horizon_astro)
        night.sunset_astro = self.observer.sun_settime(night.sunrise_prepare, mode = 'previous', horizon= horizon_astro)
        night.observable_hour = (night.sunrise_astro - night.sunset_astro).jd * 24
        night.midnight = Time((night.sunset_astro.jd + night.sunrise_astro.jd)/2, format = 'jd')
        night.time_inputted = utcdate
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
            constraint_moonsep = MoonSeparationConstraint(min = self.config['TARGET_MOONSEP'] * u.deg, max = None)
            constraint_astroplan.append(constraint_moonsep)
            constraint.moonsep = self.config['TARGET_MOONSEP']
        constraint.astroplan = constraint_astroplan
        return constraint  
    
    @property    
    def connected(self):
        return self.sql.connected
    
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
        rbs_date = celestialobject.rts_date(year = self.utcdate.datetime.year, time_grid_resolution= 1)
        targetinfo_listdict = [{'risedate' : rd, 'bestdate' : bd, 'setdate' : sd} for rd, bd, sd in rbs_date]
        
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
                
        for i, value in enumerate(tqdm(values_update_dict, desc = 'Updating DB...')):
            target_to_update = target_tbl_to_update[i]  
            self.sql.update_row(tbl_name = self.tblname, update_value = list(value.values()), update_key = list(value.keys()), id_value= target_to_update['id'], id_key = 'id')
        print(f'{len(target_tbl_to_update)} targets are updated')
    
    def select_best_targets(self,
                            utcdate : Time = Time.now(),
                            size : int = 300,
                            mode : str = 'best', # best or urgent
                            observable_minimum_hour : float = 2
                            ):
        observable_fraction_criteria = observable_minimum_hour / self.obsnight.observable_hour 
        
        if not self.sql.connected:
            self.connect()
        all_targets = self.data
        column_names_for_scoring = ['risedate', 'bestdate', 'setdate']
        
        # If one of the targets do not have the required information, calculate
        rows_to_update = [any(row[name] is None or row[name] == '' for name in column_names_for_scoring) for row in all_targets]
        target_tbl_to_update =  all_targets[rows_to_update]
        if len(target_tbl_to_update) > 0:
            self.initialize(initialize_all= True)
        
        target_tbl = self.data
        print('Checking Observability of the targets...')
        celestialobject = CelestialObject(observer = self.observer,
                                          targets_ra = target_tbl['RA'],
                                          targets_dec = target_tbl['De'],
                                          targets_name = target_tbl['objname'])
        obs_tbl = observability_table(constraints = self.constraints.astroplan, 
                                      observer = self.obsinfo.observer_astroplan, 
                                      targets = celestialobject.coordinate, 
                                      time_range = [self.obsnight.sunset_astro, self.obsnight.sunrise_astro],
                                      time_grid_resolution = 30 * u.minute)
        target_tbl_observable_idx = obs_tbl['fraction of time observable'] > observable_fraction_criteria
        target_always_idx = target_tbl['risedate'] == 'Always'
        target_neverup_idx = target_tbl['risedate'] == 'Never'
        target_normal_idx =  ~(target_always_idx | target_neverup_idx)
        target_tbl_for_scoring = target_tbl[target_tbl_observable_idx & target_normal_idx]

        print('Selecting targets with the best score...')
        if mode.upper() == 'BEST':
            target_tbl_for_scoring['days_until_bestdate'] = np.abs((Time(target_tbl_for_scoring['bestdate']) - utcdate).jd)
            target_tbl_for_scoring.sort('days_until_bestdate', reverse = False)
            return target_tbl_for_scoring[:size]
        elif mode.upper() == 'URGENT':
            target_tbl_for_scoring['days_until_setdate'] = np.abs((Time(target_tbl_for_scoring['setdate']) - utcdate).jd)
            target_tbl_for_scoring.sort('days_until_setdate', reverse = False)
            return target_tbl_for_scoring[:size]
    
    def to_Daily(self,
                 target_tbl : Table):
        self.sql.insert_rows(tbl_name = 'Daily', data = target_tbl)
    
    def update_targets_count(self,
                             targets_id : list or np.array,
                             targets_count : int or list or np.array
                             ):
        if isinstance(targets_count, int):
            targets_count = list(targets_count) * len(targets_id)
        else:
            if len(targets_id) != len(targets_count):
                raise ValueError('size of targets_id is not consistent to sie of targets_count')
        self.sql.update_row(tbl_name = self.tblname, update_value = targets_count, update_key = 'obs_count', id_value = targets_id, id_key = 'id')
    
    @property
    def data(self):
        if not self.sql.connected:
            self.connect()
        return self.sql.get_data(tbl_name = self.tblname, select_key= '*')
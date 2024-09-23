#%%
from tcspy.utils.target import MultiTargets
from tcspy.configuration import mainConfig
from tcspy.utils.databases import SQL_Connector
from tcspy.devices.observer import mainObserver
from tcspy.utils.nightsession import NightSession

from astropy.table import Table 
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import SkyCoord
import numpy as np
from astroplan import observability_table
from astroplan import AltitudeConstraint, MoonSeparationConstraint
import tqdm

# %%

class DB_Annual(mainConfig):
    """
    A class representing data from the RIS database.

    Parameters
    ----------
    utcdate : Time
    	Rename to the current time.
    tbl_name : str
    	Rename the table. 

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
    utcdate : astropy.time.Time
        The current universal time.
    obsinfo : object
        The observer and celestial body information.
    obsnight : object
        The observing information at sunset and sunrise.
    connected
        Whether the connection to the database is alive.

    Methods
    -------
    connect()
        Establish a connection to the MySQL database and set the cursor and executor.
    disconnect()
        Disconnect from the MySQL database and update the connection status flag to False.
    initialize()
    	Initializes the target table to update.
    select_best_targets()
    	Select the best observable targets for observation.
    to_Daily()
    	Inserts rows to the 'Daily' table.
    update_targets_count()
    	Update observation counts for target.
    """
    
    def __init__(self,
                 tbl_name : str = 'RIS'):
        super().__init__()       
        self.observer = mainObserver()
        self.tblname = tbl_name
        self.sql = SQL_Connector(id_user = self.config['DB_ID'], pwd_user= self.config['DB_PWD'], host_user = self.config['DB_HOSTIP'], db_name = self.config['DB_NAME'])
        self.constraints = self._set_constrints()
        self.nightsession = NightSession()

    '''
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
        Disconnect from the MySQL database and update the connection status flag to False.
        """
        self.sql.disconnect()
    '''
    def initialize(self, 
                   utcdate : Time = Time.now(),
                   initialize_all : bool = False):
        """
        Initializes and updates the target table.

        Parameters
        ----------
        initialize_all : bool
        	Whether to re-calculate all rows of the table, or only the rows that need update.
        """
        #self.connect()
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
        
        multitargetss = MultiTargets(observer = self.observer,
                                          targets_ra = target_tbl_to_update['RA'],
                                          targets_dec = target_tbl_to_update['De'],
                                          targets_name = target_tbl_to_update['objname'])
        
        # Target information 
        rbs_date = multitargetss.rts_date(year = utcdate.datetime.year, time_grid_resolution= 1)
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
                            observable_minimum_hour : float = 2,
                            n_time_grid : float = 10,
                            ):
        """
        Select the best observable targets at certain night.

        Parameters
        ----------
        utcdate : Time
        	Representing the current time.
        size : int
        	The number of targets to select.
        mode : str
        	Target selection mode which is either 'best' or 'urgent'.
        observable_minimum_hour : float
        	The minimum number of hours a target needs to be observable.
        
        Returns
        -------
        Table
        	A table containing the best targets for the night.
        """
        obsnight = self.nightsession.set_obsnight(utctime = utcdate, horizon_flat = self.config['TARGET_SUNALT_FLAT'], horizon_prepare = self.config['TARGET_SUNALT_PREPARE'], horizon_observation = self.config['TARGET_SUNALT_OBSERVATION'])
        observable_fraction_criteria = observable_minimum_hour / obsnight.observable_hour 
        
        #if not self.sql.connected:
        #    self.connect()
        all_targets = self.data
        column_names_for_scoring = ['risedate', 'bestdate', 'setdate']
        
        # If one of the targets do not have the required information, calculate
        rows_to_update = [any(row[name] is None or row[name] == '' for name in column_names_for_scoring) for row in all_targets]
        target_tbl_to_update =  all_targets[rows_to_update]
        if len(target_tbl_to_update) > 0:
            self.initialize(initialize_all= True)
        
        target_tbl = self.data
        print('Checking Observability of the targets...')
        obs_tbl = observability_table(constraints = self.constraints.astroplan, 
                                      observer = self.observer._observer,
                                      targets = SkyCoord(target_tbl['RA'], target_tbl['De'], unit = 'deg'), 
                                      time_range = [obsnight.sunset_observation, obsnight.sunrise_observation],
                                      time_grid_resolution = 30 * u.minute)
        target_tbl_observable_idx = obs_tbl['fraction of time observable'] > observable_fraction_criteria
        target_always_idx = target_tbl['risedate'] == 'Always'
        target_neverup_idx = target_tbl['risedate'] == 'Never'
        target_normal_idx =  ~(target_neverup_idx)
        target_tbl_observable = target_tbl[target_tbl_observable_idx & target_normal_idx]
        target_tbl_by_obscount = target_tbl_observable.group_by('obs_count')        
        
        # Create a time grid
        time_grid = obsnight.sunset_observation + np.linspace(0, 1, n_time_grid) * (obsnight.sunrise_observation - obsnight.sunset_observation)
        # Determine the number of targets for each time grid
        n_target_for_each_timegrid = np.full(n_time_grid, size / n_time_grid, dtype = int)
        n_target_for_each_timegrid[len(n_target_for_each_timegrid)//2] += size - sum(n_target_for_each_timegrid)

        for target_tbl_for_scoring in target_tbl_by_obscount.groups:

            multitargets_for_scoring = MultiTargets(observer = self.observer,
                                    targets_ra = target_tbl_for_scoring['RA'],
                                    targets_dec = target_tbl_for_scoring['De'],
                                    targets_name = target_tbl_for_scoring['objname']) 
            
            # Calculate the maximum altitude
            maxalt = 90 - np.abs(self.config['OBSERVER_LATITUDE'] - target_tbl_for_scoring['De'])
            
            # Track already selected targets
            selected_indices = list()

            for i, (n_target, time) in enumerate(zip(n_target_for_each_timegrid, time_grid)):
                altaz = multitargets_for_scoring.altaz(utctimes=time)
                score = altaz.alt.value / maxalt
                high_score_criteria = np.percentile(score, 90)
                high_scored_idx = ((score > high_score_criteria) & (altaz.alt.value > 30))
                
                available_indices = list(np.setdiff1d(np.arange(len(target_tbl_for_scoring))[high_scored_idx], list(selected_indices)))
                
                if len(available_indices) < n_target:
                    selected_idx = available_indices  # If not enough targets, select all available
                else:
                    selected_idx = list(np.random.choice(available_indices, n_target, replace=False))
                
                selected_indices += selected_idx
                n_target_for_each_timegrid[i] -= len(selected_idx)
            
            if len(selected_indices) == size:
                return target_tbl_for_scoring[list(selected_indices)]
                
    def to_Daily(self,
                 target_tbl : Table):
        """
        Insert targets to daily.

        Parameters
        ----------
        target_tbl : Table
        	The table containing the targets.
        """
        self.sql.insert_rows(tbl_name = 'Daily', data = target_tbl)
    
    def update_targets_count(self,
                             target_id : list,
                             count : list,
                             note : str = None
                             ):
        """
        Update observation counts for target.

        Parameters
        -------
        targets_id : list or np.array
        	A list containing the id of each target.
        targets_count : int or list or np.array
        	A list containing the count of each target or int to set the all observations to.
        """
        self.sql.update_row(tbl_name = self.tblname, update_value = [count, note], update_key = ['obs_count','note'], id_value = target_id, id_key = 'id')
    
    @property
    def data(self):
        """
        Retrieves the data from the database.

        Returns
        -------
        Table
        	The table containing the data from the database. 
        """
        #if not self.sql.connected:
        #Z    self.connect()
        return self.sql.get_data(tbl_name = self.tblname, select_key= '*')

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
# %%
if __name__ == '__main__':
    db = DB_Annual()
    #current_obscount = len(db.data[db.data['obs_count']>  0])
    tot_tilecount = len(db.data)
    #print(f'{current_obscount}/{tot_tilecount}')
# %%

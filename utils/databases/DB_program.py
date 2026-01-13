#%%
from tcspy.utils.target import MultiTargets
from tcspy.configuration import mainConfig
from tcspy.utils.connector import SQLConnector
from tcspy.devices.observer import mainObserver
from tcspy.utils.nightsession import NightSession

import os
from astropy.table import Table, vstack
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import SkyCoord
import numpy as np
from astroplan import observability_table
from astroplan import AltitudeConstraint, MoonSeparationConstraint
from tqdm import tqdm
import matplotlib.pyplot as plt
from astropy.io import ascii

# %%
class DB_Program(mainConfig):
    """
    A class representing data from the Program target database.

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
    sql : SQLConnector
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
    to_Dynamic()
    	Inserts rows to the 'Dynamic' table.
    update_targets_count()
    	Update observation counts for target.
    """
    
    def __init__(self,
                 tbl_name : str = 'Program'):
        super().__init__()       
        self.observer = mainObserver()
        self.tblname = tbl_name
        self.sql = SQLConnector(id_user = self.config['DB_ID'], pwd_user= self.config['DB_PWD'], host_user = self.config['DB_HOSTIP'], db_name = self.config['DB_NAME'])
        self.constraints = self._set_constrints()
        self.nightsession = NightSession()

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

    def change_table(self, 
                     tbl_name : str):
        self.tblname = tbl_name
    
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
        rows_to_update_id = [any(row[name] in (None, '') for name in ['id']) for row in target_tbl_all]
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
                
        for i, value in enumerate(tqdm(targetinfo_listdict, desc = 'Updating DB...')):
            target_to_update = target_tbl_to_update[i]  
            self.sql.update_row(tbl_name = self.tblname, update_value = list(value.values()), update_key = list(value.keys()), id_value= target_to_update['id'], id_key = 'id')
        print(f'{len(target_tbl_to_update)} targets are updated')
    
    def select_best_targets(self,
                            utcdate : Time = Time.now(),
                            observable_minimum_hour: float = 1,
                            n_time_grid : float = 10
                            ):
        obsnight = self.nightsession.set_obsnight(utctime = utcdate)
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
        
        all_target_tbl = self.data
        all_coords = SkyCoord(all_target_tbl['RA'], all_target_tbl['De'], unit ='deg', frame = 'icrs')

        print('Checking Observability of the targets...')
        obs_tbl = observability_table(constraints = self.constraints.astroplan, 
                                      observer = self.observer._observer,
                                      targets = all_coords,
                                      time_range = [obsnight.sunset_observation, obsnight.sunrise_observation],
                                      time_grid_resolution = 30 * u.minute)
        target_tbl_observable_idx = obs_tbl['fraction of time observable'] > observable_fraction_criteria
        target_always_idx = all_target_tbl['risedate'] == 'Always'
        target_neverup_idx = all_target_tbl['risedate'] == 'Never'
        target_normal_idx =  ~(target_neverup_idx)
        tbl = all_target_tbl[target_tbl_observable_idx & target_normal_idx]

        # Select target for observation 
        utcdate_mjd = utcdate.mjd

        #------------------------------------------------------------
        # 1) Time window: obs_starttime ≤ now ≤ obs_endtime
        #    If start is None → always allowed.
        #    If end is None   → always allowed.
        #------------------------------------------------------------
        obs_start = tbl['obs_startdate']   # Time or masked/None
        obs_end   = tbl['obs_enddate']     # Time or masked/None

        # Convert to MJD, safely handling None/masked
        def col_to_mjd(col):
            mjd = np.full(len(col), np.nan, dtype=float)
            for i, v in enumerate(col):
                if v is None:
                    continue
                try:
                    mjd[i] = v.mjd   # v is Time
                except Exception:
                    pass
            return mjd

        start_mjd = col_to_mjd(obs_start)
        end_mjd   = col_to_mjd(obs_end)

        # Condition:
        # - start is NaN (no constraint) OR start <= now
        # - end   is NaN (no constraint) OR end   >= now
        observation_idx_from_time = (
            (np.isnan(start_mjd) | (start_mjd <= utcdate_mjd))
            & (np.isnan(end_mjd)   | (end_mjd   >= utcdate_mjd))
        )

        #------------------------------------------------------------
        # 2) Count condition: obs_count < target_count
        #    If target_count is None → unlimited (always True)
        #------------------------------------------------------------
        obs_count    = np.array(tbl['obs_count'], dtype=float)
        target_count = np.array(tbl['target_count'], dtype=float)

        observation_idx_from_count = (
            (obs_count < target_count)
        )

        #------------------------------------------------------------
        # 3) Cadence condition:
        #    last_obsdate is before (now - cadence)
        #    i.e. (now - last_obsdate) ≥ cadence
        #    If last_obsdate is None → never observed → okay to observe.
        #------------------------------------------------------------
        last_obsdate = tbl['last_obstime']   # Time or None
        cadence_days = np.array(tbl['cadence'], dtype=float)  # in days

        # Build mask
        observation_idx_from_cadence = np.zeros(len(tbl), dtype=bool)

        for i, (last, cad) in enumerate(zip(last_obsdate, cadence_days)):
            # If cadence is not set or <= 0 → no cadence restriction
            if cad is None or np.isnan(cad) or cad <= 0:
                observation_idx_from_cadence[i] = True
                continue

            # If never observed → okay to observe now
            if last is None:
                observation_idx_from_cadence[i] = True
                continue

            # Check difference in days
            dt_days = (utcdate - Time(last)).to('day').value
            observation_idx_from_cadence[i] = dt_days >= cad

        #------------------------------------------------------------
        # 4) Final observable index: all conditions must be True
        #------------------------------------------------------------
        observable_idx = (
            observation_idx_from_time
            & observation_idx_from_count
            & observation_idx_from_cadence
        )

        # Apply to table
        target_tbl_to_observe = tbl[observable_idx]
        return target_tbl_to_observe

    def to_Dynamic(self,
                   target_tbl : Table):
        """
        Insert targets to Dynamic.

        Parameters
        ----------
        target_tbl : Table
        	The table containing the targets.
        """
        self.sql.insert_rows(tbl_name = 'Dynamic', data = target_tbl)
    
    def update_target(self,
                     target_id : str,
                     update_keys : list,
                     update_values : list,
                     id_key : str = 'id'
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
        self.sql.update_row(tbl_name = self.tblname, update_value = update_values, update_key = update_keys, id_value = target_id, id_key = id_key)
    
    @property
    def data(self):
        """
        Retrieves the data from the database.

        Returns
        -------
        Table
        	The table containing the data from the database. 
        """
        return self.sql.get_data(tbl_name = self.tblname, select_key= '*')

    
    def insert(self,
               target_tbl : Table):
        """
        Inserts a new record into the table.

        Parameters
        ----------
        target_tbl : Table
            An astropy table containing the target data to be inserted.
        """
        insertion_result = self.sql.insert_rows(tbl_name = self.tblname, data = target_tbl)
        return insertion_result

    def export_to_csv(self):
        """

        """
        try:
            tbl = self.data
            if not os.path.exists(self.config['DB_PROGRAMPATH']):
                os.makedirs(self.config['DB_PROGRAMPATH'], exist_ok = True)
            file_abspath = os.path.join(self.config['DB_PROGRAMPATH'], f'DB_Program.{self.config["DB_PROGRAMFORMAT"]}')
            tbl.write(file_abspath, format= self.config['DB_PROGRAMFORMAT'], overwrite=True)
            print(f"Exported Program table to {file_abspath}")
        except Exception as e:
            print(f"Failed to export data: {e}")

    def _set_constrints(self):
        class constraint: pass
        constraint_astroplan = []
        if (self.config['TARGET_MINALT'] != None) & (self.config['TARGET_MAXALT'] != None):
            constraint_altitude = AltitudeConstraint(min = self.config['TARGET_MINALT'] * u.deg, max = self.config['TARGET_MAXALT'] * u.deg, boolean_constraint = False)
            constraint_astroplan.append(constraint_altitude)
            constraint.minalt = self.config['TARGET_MINALT']
            constraint.maxalt = self.config['TARGET_MAXALT']
        # if self.config['TARGET_MOONSEP'] != None:
        #     constraint_moonsep = MoonSeparationConstraint(min = self.config['TARGET_MOONSEP'] * u.deg, max = None)
        #     constraint_astroplan.append(constraint_moonsep)
        #     constraint.moonsep = self.config['TARGET_MOONSEP']
        constraint.astroplan = constraint_astroplan
        return constraint  
# %%
if __name__ == '__main__':
    import matplotlib.pyplot as plt
    self = DB_Program(tbl_name = 'Program')

    # tbl = db.select_best_targets()
    # current_obscount = len(db.data[db.data['obs_count']>  0])
    # tot_tilecount = len(db.data)
    # print('Current_obscount = ', current_obscount)
    # print('Total_obscount_sum = ', np.sum(db.data['obs_count']))
    # print(f'{current_obscount}/{tot_tilecount}')
    #tbl_to_insert = db.data[[2665, 2666, 2523, 2524, 2385, 2386, 2252]]
    #db_IMS.insert(tbl_to_insert)
# %%
if __name__ == '__main__':
    import numpy as np
    import matplotlib.pyplot as plt
        
    survey_data = db.data
    all_coords = SkyCoord(survey_data['RA'], survey_data['De'], unit ='deg', frame = 'icrs')
    # galactic latitude cut
    survey_data['l'] = all_coords.galactic.l.value
    survey_data['b'] = all_coords.galactic.b.value
    highb_idx = np.abs(all_coords.galactic.b.value) > 85
    galcenter_idx = np.abs(all_coords.galactic.l.value) < 3
    # declination cut
    decl_idx = (all_coords.dec.value < -10) & (all_coords.dec.value > -90)
    # all cut
    total_idx1 = highb_idx & galcenter_idx# & decl_idx 
    total_idx2 = highb_idx & decl_idx & galcenter_idx

    survey_tbl = survey_data[total_idx1]
    survey_tbl2 = survey_data[total_idx2]

    
    all_data = db.data
    obs_data = all_data[all_data['obs_count'] > 0]
    high_data = all_data[all_data['obs_count'] > 3]
    intense_data = all_data[all_data['obs_count'] > 10]
    tonight_data = db.select_best_targets(size = 100)


    # Convert RA to radians and shift to [-180, 180] range
    def convert_ra(ra):
        return np.radians((ra + 180) % 360 - 180)

    # Convert Dec to radians
    def convert_dec(dec):
        return np.radians(dec)

    plt.figure(figsize=(10, 5), dpi=300)
    ax = plt.subplot(111, projection="mollweide")

    # Convert RA and Dec for plotting
    all_ra = convert_ra(survey_tbl['RA'])
    all_dec = convert_dec(survey_tbl['De'])
    survey_ra = convert_ra(survey_tbl2['RA'])
    survey_dec = convert_dec(survey_tbl2['De'])

    obs_ra = convert_ra(obs_data['RA'])
    obs_dec = convert_dec(obs_data['De'])

    high_ra = convert_ra(high_data['RA'])
    high_dec = convert_dec(high_data['De'])

    intense_ra = convert_ra(intense_data['RA'])
    intense_dec = convert_dec(intense_data['De'])
    
    tonight_ra = convert_ra(tonight_data['RA'])
    tonight_dec = convert_dec(tonight_data['De'])

    # Plot data
    ax.scatter(all_ra, all_dec, s=1, c='k', alpha=0.2)
    #ax.scatter(survey_ra, survey_dec, s=1, c='k', alpha=0.3, label="Curren|l| > 20 & Decl < -10")
    ax.scatter(obs_ra, obs_dec, s=1, c='r', alpha=0.5, label="Observed")
    ax.scatter(high_ra, high_dec, s=5, c='g', alpha=0.5, label="N_obs >3")
    ax.scatter(intense_ra, intense_dec, s=5, c='b', alpha=1.0, label="N_obs >10")
    #ax.scatter(tonight_ra, tonight_dec, s=1, c='b', alpha=1, label="Tonight scheduled")

    # Labels and grid
    ax.set_xticklabels(['14h', '16h', '18h', '20h', '22h', '0h', '2h', '4h', '6h', '8h', '10h'])
    ax.grid(True)
    plt.legend()
    plt.title(f"7DT RIS Observations on {Time.now().datetime.strftime('%Y-%m-%d')}")
    plt.show()

# %%

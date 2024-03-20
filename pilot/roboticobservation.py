


#%%
from astropy.time import Time
from threading import Event

from tcspy.action.level1 import *
from tcspy.action.level2 import *
from tcspy.action.level3 import *
from tcspy.configuration import mainConfig
from tcspy.devices import MultiTelescopes
from tcspy.devices import IntegratedDevice
from tcspy.utils.databases import DB
#%%


class RoboticObservation(mainConfig):
    
    def __init__(self, 
                 MultiTelescopes : MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = MultiTelescopes
        self.devices = MultiTelescopes.devices
        self.log = MultiTelescopes.log
        self.abort_action = abort_action
        self.DB = self.update_DB(utctime = Time.now())
        self.initialize()
    
    def initialize(self):
        
        # Initialize Daily target table 
        self.DB.Daily.initialize(initialize_all= False)
        if all(Time(self.DB.Daily.data['besttime']) < Time.now()):
            self.DB.Daily.initialize(initialize_all= True)
    
    def update_DB(self,
                  utctime : Time = Time.now()):
        print('Updating databases...')
        return DB(utctime = utctime)
    
    
    
# %%

M = MultiTelescopes([IntegratedDevice(21)])
abort_action = Event()
R = RoboticObservation(M, abort_action= abort_action)
# %%
import astropy.units as u
target, score = R.DB.Daily.best_target(Time.now() - 5 * u.hour)
R.DB.Daily.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
# %%
R.DB.Daily.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
# %%
target
# %%

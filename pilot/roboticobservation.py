


#%%
from astropy.time import Time

from tcspy.action.level1 import *
from tcspy.action.level2 import *
from tcspy.action.level3 import *
from tcspy.configuration import mainConfig
from tcspy.utils.target import singletarget
from tcspy.utils.databases import DB
#%%


class RoboticObservation(mainConfig):
    
    def __init__(self, 
                 utctime : Time = Time.now()):
        super().__init__()
        self.DB = self.update_DB(utctime = utctime)
    
    def update_DB(self,
                  utctime : Time = Time.now()):
        print('Updating databases...')
        return DB(utctime = utctime)
    
    
    
# %%

R = RoboticObservation()
# %%
import astropy.units as u
R.DB.Daily.best_target(Time.now() - 5 * u.hour)
# %%
R.DB.Daily.data
# %%

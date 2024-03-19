


#%%
from astropy.time import Time

from tcspy.utils.databases import *
from tcspy.configuration import mainConfig
#%%

class DB(mainConfig):
    
    def __init__(self,
                 utctime = Time.now()):
        super().__init__()
        self.Daily = self.update_Daily(utctime = utctime)
        self.RIS = self.update_RIS(utcdate = utctime)
    
    def update_Daily(self, utctime):
        Daily = DB_Daily(utctime = utctime, tbl_name = 'Daily')
        return Daily

    def update_RIS(self, utcdate):
        return DB_RIS(utcdate = utcdate, tbl_name = 'RIS')
# %%
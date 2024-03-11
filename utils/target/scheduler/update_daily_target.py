

#%%
from tcspy.utils.target import MultiTarget
from tcspy.configuration import mainConfig
from tcspy.utils.target.db_target import SQL_Connector
# %%

class DailyTarget(mainConfig):
    
    def __init__(self):
        super().__init__()       
    

# %%
mainConfig(unitnum= 21).config
# %%

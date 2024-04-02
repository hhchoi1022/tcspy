#%% 
# Other modules
from astropy.io import ascii
from astropy.time import Time
import time
import json
import glob
from datetime import datetime
import re

# Alpaca modules
from alpaca.observingconditions import ObservingConditions
# TCSpy modules
from tcspy.utils.logger import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig
from tcspy.utils.exception import *
from weatherupdater import WeatherUpdater
import numpy as np

# %%
class mainWeather(mainConfig):
    """
    A class for interfacing with an Alpaca weather device.

    Parameters
    ----------
    unitnum : int
        The unit number.

    Attributes
    ----------
    device : `ObservingConditions`
        The Alpaca weather device to interface with.
    status : dict
        A dictionary containing the current weather status.

    Methods
    -------
    get_status() -> dict
        Get the current weather status.
    connect() -> None
        Connect to the weather device.
    disconnect() -> None
        Disconnect from the weather device.
    is_safe() -> bool
        Check if the current weather is safe.
    """
    
    def __init__(self,
                 unitnum : int = None):

        super().__init__(unitnum = unitnum)
        self.unitnum = unitnum
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
        self.device = ObservingConditions(f"{self.config['WEATHER_HOSTIP']}:{self.config['WEATHER_PORTNUM']}",self.config['WEATHER_DEVICENUM'])
        self.updater = WeatherUpdater(unitnum = self.unitnum)#, weatherinfo_path = self.weatherinfo_path)
    
    def get_status(self):
    

        """d
        Get the current weather status.

        Returns
        -------
        status : dict
            A dictionary containing the current weather status.
        """
        
        dt_ut = datetime.strptime(Time.now().isot, '%Y-%m-%dT%H:%M:%S.%f')
        str_date = dt_ut.strftime('%y%m%d')
        directory = os.path.join(self.updater.weatherinfo_path, str_date)
        weatherinfo_list = glob.glob(directory + '/weatherinfo*.txt')
        updatetime_list =  [datetime.strptime(re.findall(pattern = f'({str_date}_\d\d\d\d\d\d)', string = file_)[0], '%y%m%d_%H%M%S'  ) for file_ in weatherinfo_list]
        
        # If there is no weather information file, generate 
        if len(updatetime_list) == 0:
            last_update_file = self.updater.update_info_file(overwrite = self.config['WEATHER_SAVE_HISTORY'])
        # Else, find the latest weather information file
        else:
            updatetime = Time(updatetime_list)
            last_update_idx =  np.argmin(np.abs((updatetime - Time(dt_ut)).jd * 86400))
            elapse_time_since_update = (np.abs((updatetime - Time(dt_ut)).jd * 86400))[last_update_idx]
            last_update_file = weatherinfo_list[last_update_idx]
            # If update time of the weather information file is larger than 2* WEATHER_UPDATETIME, update file
            if elapse_time_since_update > 2* self.config['WEATHER_UPDATETIME']: ###################
                last_update_file = self.updater.update_info_file(overwrite = self.config['WEATHER_SAVE_HISTORY'])
            
        with open(last_update_file, 'r') as f:
            weather_info = json.load(f)
        return weather_info            
        
        


        
            
        
        
        


# %%

if __name__ =='__main__':
    weather = mainWeather(unitnum = 21)
    import time
#%%
start = time.time()
print(weather.get_status())
print(time.time() - start)
    #weather.disconnect()
# %%

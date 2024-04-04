#%% 
# Other modules
from astropy.io import ascii
from astropy.time import Time
import time
import json
import glob
from datetime import datetime
import re
import os

# Alpaca modules
from alpaca.observingconditions import ObservingConditions
# TCSpy modules
from tcspy.configuration import mainConfig
from tcspy.utils.exception import *
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
    """
    
    def __init__(self):

        super().__init__()
        self.weatherinfo_path = self.config['WEATHER_PATH']
    
    def get_status(self):
    
        """
        Get the current weather status.

        Returns
        -------
        status : dict
            A dictionary containing the current weather status.
        """
        """
        Get the current weather status.

        Returns
        -------
        status : dict
            A dictionary containing the current weather status.
        """
        status = dict()
        status['update_time'] = Time.now().isot
        status['jd'] = round(Time.now().jd,6)
        status['is_connected'] = False
        status['name'] = None
        status['is_safe'] = None
        status['temperature'] = None
        status['dewpoint'] = None
        status['humidity'] = None
        status['pressure'] = None
        status['windspeed'] = None
        status['windgust'] = None
        status['winddirection'] = None
        status['skybrightness'] = None
        status['skytemperature'] = None
        status['cloudfraction'] = None
        status['rainrate'] = None
        status['fwhm'] = None
        status['constraints'] = None

        dt_ut = datetime.strptime(Time.now().isot, '%Y-%m-%dT%H:%M:%S.%f')
        str_date = dt_ut.strftime('%y%m%d')
        directory = os.path.join(self.weatherinfo_path, str_date)
        weatherinfo_list = glob.glob(directory + '/weatherinfo*.txt')
        updatetime_list =  [datetime.strptime(re.findall(pattern = f'({str_date}_\d\d\d\d\d\d)', string = file_)[0], '%y%m%d_%H%M%S'  ) for file_ in weatherinfo_list]
        
        # If there is no weather information file, generate weather info file
        if len(updatetime_list) == 0:
            last_update_file = None
            print ('No weather information file exists. Run "WeatherUpdater.py"')
        # Else, find the latest weather information file
        else:
            updatetime = Time(updatetime_list)
            last_update_idx =  np.argmin(np.abs((updatetime - Time(dt_ut)).jd * 86400))
            elapse_time_since_update = (np.abs((updatetime - Time(dt_ut)).jd * 86400))[last_update_idx]
            last_update_file = weatherinfo_list[last_update_idx]
            # If update time of the weather information file is larger than 5* WEATHER_UPDATETIME, update file
            if elapse_time_since_update > 5* self.config['WEATHER_UPDATETIME']: 
                last_update_file = None
        if last_update_file:
            with open(last_update_file, 'r') as f:
                status = json.load(f)
        return status       
# %%

if __name__ =='__main__':
    weather = mainWeather()
    import time

# %%

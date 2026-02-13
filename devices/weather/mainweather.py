#%% 
# Other modules
from astropy.io import ascii
from astropy.time import Time
import astropy.units as u
import time
import json
import glob
from datetime import datetime
import re
import os
import numpy as np
from multiprocessing import Event
import portalocker
from pathlib import Path

# Alpaca modules
from alpaca.observingconditions import ObservingConditions
# TCSpy modules
from tcspy.configuration import mainConfig
from tcspy.utils.exception import *
from tcspy.utils import Timeout

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
        Get the current weather statu.
    """
    
    def __init__(self):

        super().__init__()
        self.device = ObservingConditions(f"{self.config['WEATHER_HOSTIP']}:{self.config['WEATHER_PORTNUM']}",self.config['WEATHER_DEVICENUM'])
        self.constraints = self._get_constraints()
        self.is_running = False

    def get_status(self) -> dict:
        """
        Get the status of the Weather device

        Returns
        -------
        status : dict
            A dictionary containing the current status of the Weather device.
        """
        dt_ut = datetime.strptime(Time.now().isot, '%Y-%m-%dT%H:%M:%S.%f')
        str_date_for_dir = datetime.strptime((Time.now() - 12*u.hour).isot, '%Y-%m-%dT%H:%M:%S.%f').strftime('%y%m%d')
        
        # Define the directory and find existing files
        directory = os.path.join(self.config['WEATHER_PATH'], str_date_for_dir)
        weatherinfo_list = glob.glob(directory + f'/weatherinfo*.txt')
        
        if len(weatherinfo_list) == 0:
            status = self.update_info_file(return_status = True)
        else:
            # Extract update times from filenames
            updatetime_list =  [datetime.strptime(re.findall(pattern = r'(\d{6}_\d{6})', string = file_)[0], '%y%m%d_%H%M%S'  ) for file_ in weatherinfo_list]
            # Convert update times to astropy Time objects
            updatetime = Time(updatetime_list)
            # Find the most recent update file
            last_update_idx =  np.argmin(np.abs((updatetime - Time(dt_ut)).jd * 86400))
            elapse_time_since_update = (np.abs((updatetime - Time(dt_ut)).jd * 86400))[last_update_idx]
            last_update_file = weatherinfo_list[last_update_idx]
            
            if elapse_time_since_update > 5* self.config['WEATHER_UPDATETIME']: 
                status = self.update_info_file(return_status = True)
            else:
                with portalocker.Lock(last_update_file, 'r', timeout=10) as f:
                    status = json.load(f)      
        return status   

    def run(self, abort_action : Event):
        
        def update_status():
            if not self.device.Connected:
                self.connect()  
            print(f'WeatherUpdater activated')
            while not abort_action.is_set():
                self.update_info_file(return_status = False)
                print(f'Last weatherinfo update: {Time.now().isot}')
                time.sleep(self.config['WEATHER_UPDATETIME'])
                self.is_running = True
        try:
            update_status()
        except:
            pass
        print(f'WeatherUpdater disconnected: {Time.now().isot}')
        self.is_running = False

    @Timeout(5, 'Timeout')
    def connect(self):
        """
        Connect to the weather device.
        """
        #self._log.info('Connecting to the weather station...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
                time.sleep(0.5)
            while not self.device.Connected:
                time.sleep(0.5)
            if  self.device.Connected:
                pass
                #self._log.info('Weather device connected')
        except:
            #self._log.warning('Connection failed')
            raise ConnectionException('Connection failed')
        return True
    
    @Timeout(5, 'Timeout')
    def disconnect(self):
        """
        Disconnect from the weather device.
        """
        #self._log.info('Disconnecting weather station...')
        try:
            if self.device.Connected:
                self.device.Connected = False
                time.sleep(0.5)
            while self.device.Connected:
                time.sleep(0.5)
            if not self.device.Connected:
                pass
                #self._log.info('Weather device is disconnected')
        except:
            #self._log.warning('Disconnect failed')
            raise ConnectionException('Disconnect failed')
        return True   

    def update_info_file(self, return_status : bool = False):
        current_status = self._status
        dt_ut = datetime.strptime(current_status['update_time'], '%Y-%m-%dT%H:%M:%S.%f')
        str_date = dt_ut.strftime('%y%m%d')
        str_time = dt_ut.strftime('%H%M%S')
        str_date_for_dir = datetime.strptime((Time.now() - 12*u.hour).isot, '%Y-%m-%dT%H:%M:%S.%f').strftime('%y%m%d')
        filename = f'weatherinfo_{str_date}_{str_time}.txt'
        directory = os.path.join(self.config['WEATHER_PATH'], str_date_for_dir)
        
        # Ensure the directory exists
        os.makedirs(name = directory, exist_ok = True)
        
        file_abspath = os.path.join(directory, filename)
        
        # Write the status file to a temporary file with a lock
        with portalocker.Lock(file_abspath, 'w', timeout=10) as f:
            json.dump(current_status, f, indent=4)
            
        # [241220] Added for synching 7DT weather status to the SNU server (proton) 
        statusfile_abspath = Path(self.config['WEATHER_STATUSPATH'])

        # Create parent directory only
        statusfile_abspath.parent.mkdir(parents=True, exist_ok=True)

        with portalocker.Lock(statusfile_abspath, 'w', timeout=10) as f:
            json.dump(current_status, f, indent=4)

        # Return the status if requested
        if return_status:
            return current_status
    
    def _is_safe(self, weather_status : dict):
        """
        Check if the current weather is safe.

        Returns
        -------
        is_safe : bool
            True if the current weather is safe; False otherwise.
        """
        safe_humidity    = weather_status['humidity'] < self.constraints['HUMIDITY'] 
        safe_rainrate    = weather_status['rainrate'] < self.constraints['RAINRATE'] 
        safe_skymag      = weather_status['skybrightness'] > self.constraints['SKYMAG'] 
        safe_temperature = (weather_status['temperature'] > self.constraints['TEMPERATURE_LOWER']) & (weather_status['temperature'] < self.constraints['TEMPERATURE_UPPER'])
        safe_windspeed   = weather_status['windspeed'] < self.constraints['WINDSPEED'] 
        is_safe = safe_humidity & safe_rainrate & safe_skymag & safe_temperature & safe_windspeed
        return is_safe
    
    def _get_constraints(self):
        constraints = dict()
        constraints['HUMIDITY'] = self.config['WEATHER_HUMIDITY']
        constraints['RAINRATE'] = self.config['WEATHER_RAINRATE']
        constraints['SKYMAG'] = self.config['WEATHER_SKYMAG']
        constraints['TEMPERATURE_LOWER'] = self.config['WEATHER_TEMPERATURE_UPPER']
        constraints['TEMPERATURE_UPPER'] = self.config['WEATHER_TEMPERATURE_LOWER']
        constraints['WINDSPEED'] = self.config['WEATHER_WINDSPEED']
        return constraints

    @property
    def _status(self):
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
        status['is_safe'] = None
        status['name'] = None
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
        status['constraints'] = self.constraints

        @Timeout(15, 'Timeout (15sec) error when updating status of Weather device') 
        def update_status(status):
            if self.device.Connected:
                try:
                    status['update_time'] = Time.now().isot
                except:
                    pass
                try:
                    status['jd'] = round(Time.now().jd,6)
                except:
                    pass
                try:
                    status['name'] = self.device.Name
                except:
                    pass
                try:
                    status['temperature'] = round(self.device.Temperature,1)
                except:
                    pass
                try:
                    status['dewpoint'] = round(self.device.DewPoint,1)
                except:
                    pass
                try:
                    status['humidity'] = round(self.device.Humidity,1)
                except:
                    pass
                try:
                    status['pressure'] = round(self.device.Pressure,1)
                except:
                    pass
                try:
                    status['windspeed'] = round(self.device.WindSpeed,1)
                except:
                    pass
                try:
                    status['windgust'] = round(self.device.WindGust,1)
                except:
                    pass
                try:
                    status['winddirection'] = round(self.device.WindDirection,1)
                except:
                    pass
                try:
                    status['skybrightness'] = round(self.device.SkyQuality,2)
                except:
                    pass
                try:
                    status['skytemperature'] = round(self.device.SkyTemperature,1)
                except:
                    pass
                try:
                    status['cloudfraction'] = round(self.device.CloudCover,2)
                except:
                    pass
                try:
                    status['rainrate'] = int(self.device.RainRate)
                except:
                    pass
                try:
                    status['fwhm'] = round(self.device.StarFWHM,2)
                except:
                    pass
                try:
                    status['is_safe'] = self._is_safe(weather_status = status)
                except:
                    pass
                try:
                    status['is_connected'] = True
                except:
                    pass
            return status
        try:
            status = update_status(status)
        except:
            pass

        return status
# %%

if __name__ =='__main__':
    weather = mainWeather()
    import time

# %%

# %%

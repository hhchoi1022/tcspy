#%% 
# Other modules
from astropy.io import ascii
from astropy.time import Time
import time
import json
import os
import glob
from datetime import datetime
# Alpaca modules
from alpaca.observingconditions import ObservingConditions
# TCSpy modules
from tcspy.utils.logger import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig
from tcspy.utils.exception import *

# %%
class WeatherUpdater(mainConfig):
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
                 unitnum : int = None,
                 weatherinfo_path : 'str' = './weatherinfo'):
        super().__init__(unitnum = unitnum)
        self.unitnum = unitnum
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
        self.weatherinfo_path = weatherinfo_path
        if self.unitnum:
            self.weatherinfo_path = os.path.join(self.weatherinfo_path, self.config['MOUNT_NAME'])
        else:
            self.weatherinfo_path = os.path.join(self.weatherinfo_path, self.config['TCSPY_TEL_NAME'])
        self.constraints = self._get_constraints()
        self.device = ObservingConditions(f"{self.config['WEATHER_HOSTIP']}:{self.config['WEATHER_PORTNUM']}",self.config['WEATHER_DEVICENUM'])
        self.connect()
        
    @property
    def status(self):
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
        status['constraints'] = self.constraints

        if self.device.Connected:
            try:
                self._update()
            except:
                pass
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
                status['is_connected'] = self.device.Connected
            except:
                pass

        return status
    
    @Timeout(5, 'Timeout')
    def connect(self):
        """
        Connect to the weather device.
        """
        self._log.info('Connecting to the weather station...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
                time.sleep(0.5)
            while not self.device.Connected:
                time.sleep(0.5)
            if  self.device.Connected:
                self._log.info('Weather device connected')
        except:
            self._log.warning('Connection failed')
            raise ConnectionException('Connection failed')
        return True
    
    @Timeout(5, 'Timeout')
    def disconnect(self):
        """
        Disconnect from the weather device.
        """
        self._log.info('Disconnecting weather station...')
        try:
            if self.device.Connected:
                self.device.Connected = False
                time.sleep(0.5)
            while self.device.Connected:
                time.sleep(0.5)
            if not self.device.Connected:
                self._log.info('Weather device is disconnected')
        except:
            self._log.warning('Disconnect failed')
            raise ConnectionException('Disconnect failed')
        return True
    
    def run(self):
        while True:
            self.update_info_file(overwrite = not self.config['WEATHER_SAVE_HISTORY'])
            time.sleep(self.config['WEATHER_UPDATETIME'])
            
    
    def update_info_file(self,
                         overwrite : bool = False):
        abspath_file = self._save_info_file(weather_status= self.status)
        
        # Remove previous weather information file 
        if overwrite:
            prev_info_files = glob.glob(f'{os.path.dirname(abspath_file)}/weatherinfo*.txt')
            prev_info_files.remove(abspath_file)
            if len(prev_info_files)>0:
                [os.remove(path) for path in prev_info_files]
        return abspath_file
    
    def _save_info_file(self, weather_status : dict):
        dt_ut = datetime.strptime(weather_status['update_time'], '%Y-%m-%dT%H:%M:%S.%f')
        str_date = dt_ut.strftime('%y%m%d')
        str_time = dt_ut.strftime('%H%M%S')
        filename = f'weatherinfo_{str_date}_{str_time}.txt'
        directory = os.path.join(self.weatherinfo_path, str_date)
        if not os.path.exists(directory):
            os.makedirs(name = directory)
        abspath_file = os.path.join(directory, filename)
        with open(abspath_file, 'w') as f:
            json.dump(weather_status, f, indent=4)
        return abspath_file

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
    
    def _update(self):
        self.device.Refresh()
        


        
            
        
        
        


# %%

if __name__ =='__main__':
    weather = WeatherUpdater(unitnum = 21)
    #weather.run(overwrite = False)
    #weather.disconnect()
# %%

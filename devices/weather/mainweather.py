#%% 
# Other modules
from astropy.io import ascii
from astropy.time import Time
import time
import json
# Alpaca modules
from alpaca.observingconditions import ObservingConditions
# TCSpy modules
from tcspy.utils import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig

# %%
log = mainLogger(__name__).log()
class mainWeather(mainConfig):
    """
    A class for interfacing with an Alpaca weather device.

    Parameters
    ----------
    1. device : `ObservingConditions`
        The Alpaca weather device to interface with.

    Methods
    -------
    1. get_status() -> dict
        Get the current weather status.
    2. connect() -> None
        Connect to the weather device.
    3. disconnect() -> None
        Disconnect from the weather device.
    4. is_safe() -> bool
        Check if the current weather is safe.
    """
    
    def __init__(self,
                 device : ObservingConditions):
        super().__init__()
        self._checktime = float(self.config['WEATHER_CHECKTIME'])
        self._constraints = self._get_constraints()
        
        if isinstance(device, ObservingConditions):
            self.device = device
            self.status = self.get_status()
        else:
            log.warning('Device type is not mathced to Alpaca weather device')
            raise ValueError('Device type is not mathced to Alpaca weather device')

    def get_status(self):
        """
        Get the current weather status.

        Returns
        -------
        status : dict
            A dictionary containing the current weather status.
            Keys:
                - 'update_time': Time stamp of the status update in ISO format.
                - 'jd': Julian date of the status update, rounded to six decimal places.
                - 'name': Name of the weather device.
                - 'is_safe': Flag indicating if the weather is safe.
                - 'temperature': Current temperature.
                - 'humidity': Current humidity.
                - 'pressure': Current atmospheric pressure.
                - 'windspeed': Current wind speed.
                - 'skybrightness': Current sky brightness.
                - 'cloudfraction': Current cloud fraction.
                - 'rainrate': Current rain rate.
                - 'fwhm': Current full-width at half-maximum of stars.
        """

        status = dict()
        status['update_time'] = Time.now().iso
        status['jd'] = round(Time.now().jd,6)
        status['name'] = None
        status['is_safe'] = None
        status['temperature'] = None
        status['humidity'] = None
        status['pressure'] = None
        status['windspeed'] = None
        status['skybrightness'] = None
        status['cloudfraction'] = None
        status['rainrate'] = None
        status['fwhm'] = None
        status['is_connected'] = None
        try:
            if self.device.Connected:
                self._update()
                try:
                    status['update_time'] = Time.now().iso
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
                    status['is_safe'] = self.is_safe()
                except:
                    pass
                try:
                    status['temperature'] = self._get_status_updatetime('Temperature', 1)
                except:
                    pass
                try:
                    status['humidity'] = self._get_status_updatetime('Humidity', 1)
                except:
                    pass
                try:
                    status['pressure'] = self._get_status_updatetime('Pressure', 1)
                except:
                    pass
                try:
                    status['windspeed'] = self._get_status_updatetime('WindSpeed', 1)
                except:
                    pass
                try:
                    status['skybrightness'] = self._get_status_updatetime('SkyQuality', 3)
                except:
                    pass
                try:
                    status['cloudfraction'] = self._get_status_updatetime('CloudCover', 2)
                except:
                    pass
                try:
                    status['rainrate'] = self._get_status_updatetime('RainRate', 2)
                except:
                    pass
                try:
                    status['fwhm'] = self._get_status_updatetime('StarFWHM', 2)
                except:
                    pass
                try:
                    status['is_connected'] = self.device.Connected
                except:
                    pass
        except:
            pass
        return status
    
    @Timeout(5, 'Timeout')
    def connect(self):
        """
        Connect to the weather device.
        """
        
        log.info('Connecting to the weather station...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
            while not self.device.Connected:
                time.sleep(self._checktime)
            if  self.device.Connected:
                log.info('Weather device connected')
        except:
            log.warning('Connection failed')
        self.status = self.get_status()
    
    def disconnect(self):
        """
        Disconnect from the weather device.
        """
        
        self.device.Connected = False
        log.info('Disconnecting the weather device...')
        while self.device.Connected:
            time.sleep(self._checktime)
        if not self.device.Connected:
            log.info('Weather device disconnected')
        self.status = self.get_status()

    def is_safe(self):
        """
        Check if the current weather is safe.

        Returns
        -------
        1. is_safe : bool
            True if the current weather is safe; False otherwise.
        """
        
        self._update()
        safe_humidity    = self.device.Humidity < self._constraints['HUMIDITY'] 
        safe_rainrate    = self.device.RainRate < self._constraints['RAINRATE'] 
        safe_skymag      = self.device.SkyQuality > self._constraints['SKYMAG'] 
        safe_temperature = (self.device.Temperature > self._constraints['TEMPERATURE_LOWER']) & (self.device.Temperature < self._constraints['TEMPERATURE_UPPER'])
        safe_windspeed   = self.device.WindSpeed < self._constraints['WINDSPEED'] 
        is_safe = safe_humidity & safe_rainrate & safe_skymag & safe_temperature & safe_windspeed
        return is_safe
    
    def _get_constraints(self):
        """
        Get the weather constraints from a file.

        Returns
        -------
        1. constraints : dict
            A dictionary containing the weather constraints.
            Keys:
                - 'HUMIDITY': Maximum humidity.
                - 'RAINRATE': Maximum rain rate.
                - 'SKYMAG': Minimum sky brightness.
                - 'TEMPERATURE_LOWER': Minimum temperature.
                - 'TEMPERATURE_UPPER': Maximum temperature.
                - 'WINDSPEED': Maximum wind speed.
        """
        
        with open(self.config['WEATHER_CONSTRAINTSFILE'], 'r') as f:
            return json.load(f)
    
    def _get_status_updatetime(self,
                               key : str,
                               digit : int = 1
                               ):
        """
        Get the value and the last update time of a weather parameter.

        Parameters
        ----------
        1. key : str
            The weather parameter.
        2. digit : int, optional
            The number of decimal places to round the value.

        Returns
        -------
        1. data : dict
            A dictionary containing the value and the last update time of the weather parameter.
            Keys:
                - 'value': The value of the weather parameter, rounded to `digit` decimal places.
                - 'last_update_seconds': The number of seconds since the last update of the weather parameter.
        """
        
        data = dict()
        data['value'] = round(getattr(self.device, key),digit)
        data['last_update_seconds'] = round(self.device.TimeSinceLastUpdate(key),2)
        return data
    
    def _update(self):
        """
        Update the weather device status.
        """
        
        self.device.Refresh()
        


        
            
        
        
        


# %%

if __name__ =='__main__':
    dev = ObservingConditions('127.0.0.1:32323',0)
    weather = mainWeather(dev)
    weather.connect()
    print(weather.is_safe())
    weather.disconnect()
#%%


# %%

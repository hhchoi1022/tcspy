#%%
from astropy.io import ascii
from astropy.time import Time
import time
from datetime import datetime
import os
import glob
import re
import numpy as np
import json

from alpaca.safetymonitor import SafetyMonitor

from tcspy.utils.logger import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig
from tcspy.utils.exception import *
# %%
class mainSafetyMonitor(mainConfig):
    """
    A class that provides a wrapper for the Alpaca SafetyMonitor device.

    Parameters
    ----------
    unitnum : int
        The unit number.

    Attributes
    ----------
    device : SafetyMonitor
        The SafetyMonitor device object to be used.
    status : dict
        A dictionary containing the current status of the SafetyMonitor device.

    Methods
    -------
    get_status() -> dict
        Get the status of the SafetyMonitor device.
    connect()
        Connect to the SafetyMonitor device.
    disconnect()
        Disconnect from the SafetyMonitor device.
    """
    
    def __init__(self):        
        super().__init__()
        self.safemonitorinfo_path = self.config['SAFEMONITOR_PATH']
        self.device = SafetyMonitor(f"{self.config['SAFEMONITOR_HOSTIP']}:{self.config['SAFEMONITOR_PORTNUM']}",self.config['SAFEMONITOR_DEVICENUM'])
        
    def get_status(self) -> dict:
        """
        Get the status of the SafetyMonitor device

        Returns
        -------
        status : dict
            A dictionary containing the current status of the SafetyMonitor device.
        """
        status = dict()        
        status['update_time'] = Time.now().isot
        status['jd'] = round(Time.now().jd, 6)
        status['name'] = None
        status['is_connected'] = False
        status['is_safe'] = None
        
        dt_ut = datetime.strptime(Time.now().isot, '%Y-%m-%dT%H:%M:%S.%f')
        str_date = dt_ut.strftime('%y%m%d')
        directory = os.path.join(self.safemonitorinfo_path)
        safemonitorinfo_list = glob.glob(directory + f'/safemonitorinfo*.txt')
        updatetime_list =  [datetime.strptime(re.findall(pattern = f'(\d\d\d\d\d\d_\d\d\d\d\d\d)', string = file_)[0], '%y%m%d_%H%M%S'  ) for file_ in safemonitorinfo_list]

        # If there is no weather information file, generate weather info file
        if len(updatetime_list) == 0:
            last_update_file = None
            print ('No safetymonitor information file exists. Run "SafetyMonitorUpdater.py"')
        # Else, find the latest weather information file
        else:        
            updatetime = Time(updatetime_list)
            last_update_idx =  np.argmin(np.abs((updatetime - Time(dt_ut)).jd * 86400))
            elapse_time_since_update = (np.abs((updatetime - Time(dt_ut)).jd * 86400))[last_update_idx]
            last_update_file = safemonitorinfo_list[last_update_idx]
            # If update time of the weather information file is larger than 5* WEATHER_UPDATETIME, update file
            if elapse_time_since_update > 5* self.config['SAFEMONITOR_UPDATETIME']: 
                last_update_file = None
        if last_update_file:
            with open(last_update_file, 'r') as f:
                status = json.load(f)
        return status
    
    @Timeout(5, 'Timeout')
    def connect(self):
        """
        Connect to the SafetyMonitor device
        """
        #self._log.info('Connecting to the SafetyMonitor device...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
                time.sleep(0.5)
            while not self.device.Connected:
                time.sleep(0.5)
            if  self.device.Connected:
                pass
                #self._log.info('SafetyMonitor is connected')
        except:
            #self._log.warning('Connection failed')
            raise ConnectionException('Connection failed')
        return True
    
    @Timeout(5, 'Timeout')
    def disconnect(self):
        """
        Disconnect from the SafetyMonitor device
        """
        #self._log.info('Disconnecting SafetyMonitor device...')
        try:
            if self.device.Connected:
                self.device.Connected = False
                time.sleep(0.5)
            while self.device.Connected:
                time.sleep(0.5)
            if not self.device.Connected:
                pass
                #self._log.info('SafetyMonitor is disconnected')
        except:
            #self._log.warning('Disconnect failed')
            raise ConnectionException('Disconnect failed')
        return True
# %%
if __name__ == '__main__':
    safe = mainSafetyMonitor()
    safe.connect()
    safe.get_status()

# %%

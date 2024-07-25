#%%
from astropy.io import ascii
from astropy.time import Time
import astropy.units as u
import time
import os
import glob
import re
import numpy as np
import json
from datetime import datetime
from astropy.time import Time
from multiprocessing import Event

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
        super().__init__(21)
        self.device = SafetyMonitor(f"{self.config['SAFEMONITOR_HOSTIP']}:{self.config['SAFEMONITOR_PORTNUM']}",self.config['SAFEMONITOR_DEVICENUM'])
        self.is_running = False


    def get_status(self) -> dict:
        """
        Get the status of the SafetyMonitor device

        Returns
        -------
        status : dict
            A dictionary containing the current status of the SafetyMonitor device.
        """
        dt_ut = datetime.strptime(Time.now().isot, '%Y-%m-%dT%H:%M:%S.%f')
        str_date = dt_ut.strftime('%y%m%d')
        str_date_for_dir = datetime.strptime((Time.now() - 12*u.hour).isot, '%Y-%m-%dT%H:%M:%S.%f').strftime('%y%m%d')
        directory = os.path.join(self.config['SAFEMONITOR_PATH'], str_date_for_dir)
        safemonitorinfo_list = glob.glob(directory + f'/safemonitorinfo*.txt')
        updatetime_list =  [datetime.strptime(re.findall(pattern = f'(\d\d\d\d\d\d_\d\d\d\d\d\d)', string = file_)[0], '%y%m%d_%H%M%S'  ) for file_ in safemonitorinfo_list]
        
        if len(updatetime_list) == 0:
            status = self.update_info_file(return_status = True)
        else:
            updatetime = Time(updatetime_list)
            last_update_idx =  np.argmin(np.abs((updatetime - Time(dt_ut)).jd * 86400))
            elapse_time_since_update = (np.abs((updatetime - Time(dt_ut)).jd * 86400))[last_update_idx]
            last_update_file = safemonitorinfo_list[last_update_idx]
            if elapse_time_since_update > 5* self.config['SAFEMONITOR_UPDATETIME']: 
                status = self.update_info_file(return_status = True)
            else:
                with open(last_update_file, 'r') as f:
                    status = json.load(f)      
        return status   

    def run(self, abort_action : Event):
        if not self.device.Connected:
            self.connect()  
        print(f'SafetyMonitorUpdater activated')
        while not abort_action.is_set():
            self.update_info_file(return_status = False)
            print(f'Last safemonitorinfo update: {Time.now().isot}')
            time.sleep(self.config['SAFEMONITOR_UPDATETIME'])
            self.is_running = True
        print(f'SafetyMonitorUpdater disconnected: {Time.now().isot}')

        self.is_running = False

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
    
    def update_info_file(self, return_status : bool = False):
        current_status = self._status
        dt_ut = datetime.strptime(current_status['update_time'], '%Y-%m-%dT%H:%M:%S.%f')
        str_date = dt_ut.strftime('%y%m%d')
        str_time = dt_ut.strftime('%H%M%S')
        str_date_for_dir = datetime.strptime((Time.now() - 12*u.hour).isot, '%Y-%m-%dT%H:%M:%S.%f').strftime('%y%m%d')
        filename = f'safemonitorinfo_{str_date}_{str_time}.txt'
        directory = os.path.join(self.config['SAFEMONITOR_PATH'], str_date_for_dir)
        if not os.path.exists(directory):
            os.makedirs(name = directory)
        abspath_file = os.path.join(directory, filename)
        with open(abspath_file, 'w') as f:
            json.dump(current_status, f, indent=4)
        if return_status:
            return current_status
    
    @property
    def _status(self):
        """
        Get the current weather status from the device.

        Returns
        -------
        status : dict
            A dictionary containing the current weather status.
        """
        status = dict()
        status['update_time'] = Time.now().isot
        status['jd'] = round(Time.now().jd, 6)
        status['is_connected'] = False
        status['is_safe'] = None
        status['name'] = None

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
                status['is_safe'] = self.device.IsSafe
            except:
                pass
            try:
                status['is_connected'] = self.device.Connected
            except:
                pass
        return status
    
# %%
if __name__ == '__main__':
    safe = mainSafetyMonitor()
    safe.connect()
    safe.get_status()
    safe.run(abort_action = Event())

# %%

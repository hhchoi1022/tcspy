#%% 
# Other modules
from astropy.io import ascii
from astropy.time import Time
import time
import json
import os
import glob
from threading import Event
from datetime import datetime
# TCSpy modules
from tcspy.utils.exception import *
from tcspy.devices.safetymonitor import mainSafetyMonitor
# %%
class SafetyMonitorUpdater(mainSafetyMonitor):
    """
    A class for interfacing with an Alpaca  device.

    Parameters
    ----------
    unitnum : int
        The unit number.

    Attributes
    ----------
    device : `ObservingConditions`
        The Alpaca weather device to interface with.

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
    
    def __init__(self):
        super().__init__()
        self.is_running = False
    
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
    
    def run(self, abort_action : Event):
        if not self.device.Connected:
            self.connect()  
        print(f'SafetyMonitorUpdater activated')
        while not abort_action.is_set():
            self.update_info_file(overwrite = not self.config['SAFEMONITOR_SAVE_HISTORY'])
            
            print(f'Last safemonitorinfo update: {Time.now().isot}')
            time.sleep(self.config['SAFEMONITOR_UPDATETIME'])
            self.is_running = True
        print(f'SafetyMonitorUpdater disconnected: {Time.now().isot}')

        self.is_running = False
            
    
    def update_info_file(self,
                         overwrite : bool = False):
        abspath_file = self._save_info_file(safemonitor_status= self._status)
        
        # Remove previous safetymonitor information file 
        if overwrite:
            prev_info_files = glob.glob(f'{os.path.dirname(abspath_file)}/safemonitorinfo*.txt')
            prev_info_files.remove(abspath_file)
            if len(prev_info_files)>0:
                [os.remove(path) for path in prev_info_files]
        return abspath_file
    
    def _save_info_file(self, safemonitor_status : dict):
        dt_ut = datetime.strptime(safemonitor_status['update_time'], '%Y-%m-%dT%H:%M:%S.%f')
        str_date = dt_ut.strftime('%y%m%d')
        str_time = dt_ut.strftime('%H%M%S')
        filename = f'safemonitorinfo_{str_date}_{str_time}.txt'
        directory = os.path.join(self.safemonitorinfo_path)
        if not os.path.exists(directory):
            os.makedirs(name = directory)
        abspath_file = os.path.join(directory, filename)
        with open(abspath_file, 'w') as f:
            json.dump(safemonitor_status, f, indent=4)
        return abspath_file

        


# %%

if __name__ =='__main__':
    safe = SafetyMonitorUpdater()
    
    safe.run(Event())
    #weather.disconnect()
# %%

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

from alpaca.switch import Switch
from tcspy.utils.logger import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig
from tcspy.utils.exception import *
import portalocker
# %%
class mainSwitch(mainConfig):
    """
    A class that provides a wrapper for the Alpaca Switch device.

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
    
    def __init__(self,
                 unitnum : int):        
        super().__init__(unitnum = unitnum)
        self.device = Switch(f"{self.config['SWITCH_HOSTIP']}:{self.config['SWITCH_PORTNUM']}",self.config['SWITCH_DEVICENUM'])
        self._allswitch = self._get_all_switchname()
        self.switch = self._set_devices()
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()

    def get_status(self):
        """
        dummy function 
        """
        return {}
    
    def _get_all_switchname(self):
        num_switch = self.device.MaxSwitch
        all_switchname = {}
        for i in range(num_switch):
            all_switchname[i] = self.device.GetSwitchDescription(i)
        return all_switchname
        
    def _set_devices(self):
        devices = dict()
        for device_type in self.config['SWITCH_TYPES']:
            devicetype_key = f'SWITCH_KEY_{device_type}'
            for id_, name in self._allswitch.items():
                if self.config[devicetype_key] in name:
                    devices[device_type] = id_
        return devices
            
    def switch_on(self, device_type : str):
        self._log.info(f'Turning on {device_type}...')
        device_type = device_type.upper()
        if device_type not in self.switch.keys():
            raise ValueError(f'{device_type} is not in the switch list')
        self.device.SetSwitch(self.switch[device_type], True)
        self._log.info(f'Power of {device_type} is on')
    
    def switch_off(self, device_type : str):
        self._log.info(f'Turning off {device_type}...')
        device_type = device_type.upper()
        if device_type not in self.switch.keys():
            raise ValueError(f'{device_type} is not in the switch list')
        self.device.SetSwitch(self.switch[device_type], False)
        self._log.info(f'Power of {device_type} is off')

    

# %%
if __name__ == '__main__':
    S = mainSwitch(1)
    S.switch_on('camera')
# %%

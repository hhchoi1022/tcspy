#%%
import time
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger

class Disconnect(Interface_Runnable):
    
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()
    
    def run(self,
            **kwargs):
        
        self._log.info(f'[{type(self).__name__}]" is triggered.')
        # disconnect devices
        devices_status = self.telescope_status.dict
        for device_name in self.telescope.devices.keys():
            if self.abort_action.is_set():
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                return False
            device = self.telescope.devices[device_name]
            status = devices_status[device_name]
            try:
                device.disconnect()
            except:
                pass

        # check the device connection
        devices_status = self.telescope_status.dict
        self._log.info('Checking devices connection...')
        self._log.info('='*30)
        for device_name in self.telescope.devices.keys():
            if not self.abort_action.is_set():
                device = self.telescope.devices[device_name]
                status = devices_status[device_name]
                if not status == 'disconnected':
                    self._log.critical(f'{device_name} cannot be disconnected. Check the ASCOM Remote Server')
                else:
                    self._log.info(f'{device_name} : Disconnected')
            else:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
        
        self._log.info('='*30)
        self._log.info(f'[{type(self).__name__}] is finished.')
        time.sleep(1)
        devices_status = self.telescope_status.dict
        return devices_status 
    
    def abort(self):
        return 
# %%
if __name__ == '__main__':
    tel1 = SingleTelescope(unitnum = 1)
    tel2 = SingleTelescope(unitnum = 2)
    Disconnect(tel1).run()
    Disconnect(tel2).run()
    

#%%
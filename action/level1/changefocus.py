#%%
from threading import Event

from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.utils.logger import mainLogger
#%%

class ChangeFocus(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()

    def run(self,
            position: int):
        # Check device connection
        if self.IDevice_status.focuser.lower() == 'disconnected':
            self._log.critical(f'Focuser is disconnected. Action "{type(self).__name__}" is not triggered')
            return 
        
        # If not aborted, execute the action
        if not self.abort_action.is_set():
            self._log.info(f'[{type(self).__name__}] is triggered.')
            if self.IDevice_status.focuser.lower() == 'idle':
                self.IDevice.focuser.move(position = position)
            self._log.info(f'[{type(self).__name__}] is finished.')
        else:
            self.abort()
    
    def abort(self):
        status_focuser = self.IDevice_status.focuser.lower()
        if status_focuser == 'disconnected':
            self._log.critical(f'Focuser is disconnected. Action "{type(self).__name__}" is not aborted')
            return 
        elif status_focuser == 'busy':
            self.IDevice.focuser.abort()
        else:
            pass 

#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger

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
            return False
        
        # If not aborted, execute the action
        if not self.abort_action.is_set():
            self._log.info(f'[{type(self).__name__}] is triggered.')
            if self.IDevice_status.focuser.lower() == 'idle':
                result_move = self.IDevice.focuser.move(position = position)
            if not self.abort_action.is_set():
                if result_move:
                    self._log.info(f'[{type(self).__name__}] is finished.')
                else:
                    return False
            else:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                return False
        else:
            self.abort()
            return False
        return True
    
    def abort(self):
        status_focuser = self.IDevice_status.focuser.lower()
        if status_focuser == 'disconnected':
            self._log.critical(f'Focuser is disconnected. Action "{type(self).__name__}" is not aborted')
            return 
        elif status_focuser == 'busy':
            self.IDevice.focuser.abort()
        else:
            pass 

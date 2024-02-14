#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class FansOff(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()

    def run(self):
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        if self.IDevice_status.focuser.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: focuser is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: focuser is disconnected.')
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
         
        # Start action
        try:
            result_fansoff = self.IDevice.focuser.fans_off()
        except FocusFansFailedException:
            self._log.critical(f'[{type(self).__name__}] is failed: fan operation failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: fan operation failure.')          

        if result_fansoff:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
    
    def abort(self):
        pass 

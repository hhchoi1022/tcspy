#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger

class TrackingOff(Interface_Runnable, Interface_Abortable):
    
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
        if self.IDevice_status.telescope.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            return False
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
            return False
        
        # Start action
        status_telescope = self.IDevice_status.telescope.lower()
        if status_telescope == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            return False
        elif status_telescope == 'parked' :
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is parked.')
            return False
        else:
            result_tracking = self.IDevice.telescope.tracking_off()
            
        if result_tracking:
            self._log.info(f'[{type(self).__name__}] is finished.')
        else:
            self._log.critical(f'[{type(self).__name__}] is failed: telescope trackingOff failure.')
            return False
        return True
        
    def abort(self):
        status_telescope = self.IDevice_status.telescope.lower()
        if status_telescope == 'busy':
            self.IDevice.telescope.abort()
        else:
            pass
#%%
from threading import Event
from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class SlewAltAz(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()
    
    def run(self,
            alt : float = None,
            az : float = None,
            **kwargs):
        
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        telescope = self.IDevice.telescope  
        status_telescope = self.IDevice_status.telescope.lower()
        if status_telescope == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: telescope is disconnected.')

        # Check abort_action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Start action
        
        if status_telescope == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: telescope is disconnected.')
        elif status_telescope == 'parked' :
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is parked.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: telescope is parked.')
        elif status_telescope == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: telescope is busy.')
        else:
            try:
                result_slew = telescope.slew_altaz(alt = float(alt),
                                                   az = float(az),
                                                   abort_action = self.abort_action,
                                                   tracking = False)
            except SlewingFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: telescope slew_altaz failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: telescope slew_altaz failure.')
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        if result_slew:
            self._log.info(f'[{type(self).__name__}] is finished.')    
        return True            
    
    def abort(self):
        status_telescope = self.IDevice_status.telescope.lower()
        if status_telescope == 'busy':
            self.IDevice.telescope.abort()
        else:
            pass 
#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = )
    abort_action = Event()
    s =SlewAltAz(device, abort_action)
    s.run(alt=20, az= 270, tracking = True)  
    

# %%

#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import * 

class Warm(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.Idevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()

    def run(self,
            settemperature : float,
            tolerance : float = 1):
        
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        if self.Idevice_status.camera.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: camera is disconnected.')
            return ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')

        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        try:
            result_warm = self.IDevice.camera.warm(settemperature = settemperature,
                                                   tolerance= tolerance,
                                                   abort_action = self.abort_action)
        except WarmingFailedException:
            self._log.critical(f'[{type(self).__name__}] is failed: camera warming failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: camera warming failure.')
        except AbortionException:
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
                        
        if result_warm:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True 
            
    
    def abort(self):
        pass

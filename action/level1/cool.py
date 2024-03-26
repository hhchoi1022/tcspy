#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class Cool(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()

    def run(self,
            settemperature : float,
            tolerance : float = 1):
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        if self.telescope_status.camera.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: camera is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        # Start action
        try:
            result_cool = self.telescope.camera.cool(settemperature = settemperature, 
                                                   tolerance = tolerance,
                                                   abort_action = self.abort_action)
        except CoolingFailedException:
            self._log.critical(f'[{type(self).__name__}] is failed: camera cool failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: camera cool failure.')
        except AbortionException:
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
            
        if result_cool:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
    
    def abort(self):
        if self.telescope.camera.device.CoolerOn:
            if self.telescope.camera.device.CCDTemperature < self.telescope.camera.device.CCDTemperature -20:
                self._log.critical(f'Turning off when the CCD Temperature below ambient may lead to damage to the sensor.')
                self.telescope.camera.cooler_off()
            else:
                self.telescope.camera.cooler_off()
        else:
            pass
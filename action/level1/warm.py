#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import * 

class Warm(Interface_Runnable, Interface_Abortable):
    
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
            return ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')

        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        try:
            result_warm = self.telescope.camera.warm(settemperature = settemperature,
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

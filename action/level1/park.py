#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import * 

class Park(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()

    def run(self):
        
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        status_mount = self.telescope_status.mount.lower()
        if status_mount == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is disconnected.')
            return ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')

        # Start action
        
        if status_mount == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is busy.')
        else:
            try:
                result_park = self.telescope.mount.park(abort_action = self.abort_action)
            except ParkingFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed')
                ActionFailedException(f'[{type(self).__name__}] is failed: mount park failure.')
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')        

        if result_park:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
            
    def abort(self):
        status_mount = self.telescope_status.mount.lower()
        if status_mount == 'busy':
            self.telescope.mount.abort()
        else:
            pass
#%%
if __name__ == '__main__':
    device = SingleTelescope(unitnum = 8)
    abort_action = Event()
    s =Park(device, abort_action= abort_action)
    s.run()

# %%

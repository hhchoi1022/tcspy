#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.utils.logger import mainLogger
from tcspy.interfaces import *
from tcspy.utils.exception import *

class Unpark(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()

    def run(self):
        # Check device connection
        self._log.info(f'[{type(self).__name__}] is triggered.')
        status_mount = self.telescope_status.mount.lower()
        if status_mount == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')

        # Start action
        if status_mount == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is busy.')
        else:
            try:
                result_unpark = self.telescope.mount.unpark()
            except ParkingFailedException:
                self._log.info(f'[{type(self).__name__}] is finished.')
                self._log.critical(f'[{type(self).__name__}] is failed')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: mount unpark failure.')
                
        if result_unpark:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
    
    def abort(self):
        return

#%%
if __name__ == '__main__':
    device = SingleTelescope(unitnum = 2)
    abort_action = Event()
    s =Unpark(device, abort_action= abort_action)
    s.run()

# %%

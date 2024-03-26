#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class TrackingOff(Interface_Runnable, Interface_Abortable):
    
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
        if self.telescope_status.mount.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')
        
        # Start action
        status_mount = self.telescope_status.mount.lower()
        if status_mount == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')
        elif status_mount == 'parked' :
            self._log.critical(f'[{type(self).__name__}] is failed: mount is parked.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is parked.')
        else:
            try:
                result_tracking = self.telescope.mount.tracking_off()
            except TrackingFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: mount trackingOff failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: mount trackingOff failure.')

        if result_tracking:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
        
    def abort(self):
        return 
#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class SlewRADec(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()
    
    def run(self,
            ra : float = None,
            dec : float = None,
            **kwargs):
        
        # Check device connection
        mount = self.telescope.mount
        status_mount = self.telescope_status.mount.lower()
        if status_mount == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')

        # Check abort_action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Start action
        self._log.info(f'[{type(self).__name__}] is triggered.')
        if status_mount == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')
        elif status_mount == 'parked' :
            self._log.critical(f'[{type(self).__name__}] is failed: mount is parked.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is parked.')
        elif status_mount == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is busy.')
        else:
            try:
                result_slew = mount.slew_radec(ra = float(ra),
                                                   dec = float(dec),
                                                   abort_action = self.abort_action,
                                                   tracking = True)
            except SlewingFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: mount slew_altaz failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: mount slew_altaz failure.')
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        if result_slew:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
    
    # For faster trigger of abort action
    def abort(self):
        status_mount = self.telescope_status.mount.lower()
        if status_mount == 'busy':
            self.telescope.mount.abort()
        else:
            pass   
# %%

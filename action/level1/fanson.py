#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class FansOn(Interface_Runnable, Interface_Abortable):
    
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
        if self.telescope_status.focuser.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: focuser is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: focuser is disconnected.')
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
         
        # Start action
        try:
            result_fanson = self.telescope.focuser.fans_on()
        except FocusFansFailedException:
            self._log.critical(f'[{type(self).__name__}] is failed: fan operation failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: fan operation failure.')          

        if result_fanson:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
    
    def abort(self):
        pass 
